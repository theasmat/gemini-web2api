"""HTTP server: OpenAI-compatible API endpoints."""
import json
import time
import uuid
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

import os
import threading
from .config import CONFIG, find_config, find_auth_file, get_default_auth_path, get_global_config_dir
from .models import MODELS, resolve_model
from .gemini import generate, generate_stream, log, get_auth_details, clear_auth, HAS_HTTPX
from .dashboard import render_dashboard
from .tools import messages_to_prompt, parse_tool_calls, google_contents_to_prompt, parse_google_function_calls
from .multimodal import detect_image_mime, fetch_image_bytes, upload_image
from . import __version__

_SERVER_START_TIME = time.time()
_REQUEST_LOGS = []
_LOGS_LOCK = threading.Lock()
_TOTAL_REQUESTS = 0


def _record_request_log(client: str, method: str, path: str, model: str, status: int, duration_ms: int, error: str = None):
    global _TOTAL_REQUESTS
    with _LOGS_LOCK:
        _TOTAL_REQUESTS += 1
        entry = {
            "id": _TOTAL_REQUESTS,
            "time": time.strftime("%H:%M:%S"),
            "client": client,
            "method": method,
            "path": path,
            "model": model or "-",
            "status": status,
            "duration_ms": duration_ms,
            "error": error
        }
        _REQUEST_LOGS.insert(0, entry)
        if len(_REQUEST_LOGS) > 100:
            _REQUEST_LOGS.pop()


def _usage(prompt: str, text: str) -> dict:
    p = len(prompt) // 4
    c = len(text or "") // 4
    return {"prompt_tokens": p, "completion_tokens": c, "total_tokens": p + c}


def _upload_images(images: list) -> list:
    """Upload images and return list of file references. Returns None if no images."""
    if not images:
        return None
    file_refs = []
    for item in images:
        if not (isinstance(item, tuple) and len(item) == 2):
            continue
        data, mime = item
        if isinstance(data, str):
            data = fetch_image_bytes(data)
            mime = mime or "image/png"
        if not data:
            raise RuntimeError("image fetch failed")
        mime = detect_image_mime(data, mime or "image/png")
        try:
            ref = upload_image(data, "image.png", mime or "image/png")
            file_refs.append(ref)
        except Exception as e:
            raise RuntimeError(f"image upload failed: {e}") from e
    return file_refs if file_refs else None


class GeminiHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        client_ip = self.client_address[0] if self.client_address else "-"
        log(f"{client_ip} {fmt % args}")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html: str, status=200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _start_sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def _parse_body(self, body: bytes) -> dict:
        try:
            return json.loads(body)
        except (json.JSONDecodeError, ValueError):
            return None

    def _read_request_body(self) -> bytes:
        transfer_encoding = self.headers.get("Transfer-Encoding", "")
        if "chunked" in transfer_encoding.lower():
            chunks = []
            while True:
                size_line = self.rfile.readline()
                if not size_line:
                    break
                size_text = size_line.split(b";", 1)[0].strip()
                try:
                    size = int(size_text, 16)
                except ValueError:
                    raise ValueError("invalid chunked request body")
                if size == 0:
                    while True:
                        trailer = self.rfile.readline()
                        if trailer in (b"\r\n", b"\n", b""):
                            break
                    break
                chunks.append(self.rfile.read(size))
                self.rfile.read(2)
            return b"".join(chunks)

        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length) if length else b""

    def _authorized(self):
        keys = CONFIG.get("api_keys") or []
        if not keys:
            return True
        # Authorization: Bearer <key>
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer ") and auth[7:] in keys:
            return True
        # header keys (OpenAI x-api-key / Google x-goog-api-key)
        for h in ("x-api-key", "x-goog-api-key"):
            if self.headers.get(h, "") in keys:
                return True
        # query param ?key= (Gemini CLI native style)
        if "?" in self.path:
            for pair in self.path.split("?", 1)[1].split("&"):
                if pair.startswith("key=") and pair[4:] in keys:
                    return True
        return False

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        client_ip = self.client_address[0] if self.client_address else "-"
        try:
            # Dashboard routes
            if self.path in ("/dash", "/dash/", "/dashboard"):
                self.send_html(render_dashboard())
                return

            # API Status endpoint
            if self.path == "/api/status":
                uptime_sec = int(time.time() - _SERVER_START_TIME)
                status_payload = {
                    "status": "ok",
                    "version": __version__,
                    "uptime_sec": uptime_sec,
                    "host": CONFIG.get("host", "0.0.0.0"),
                    "port": CONFIG.get("port", 8081),
                    "default_model": CONFIG.get("default_model", "gemini-3.6-flash"),
                    "temporary_chats": CONFIG.get("temporary_chats", False),
                    "proxy": CONFIG.get("proxy"),
                    "api_keys": CONFIG.get("api_keys", []),
                    "streaming_engine": "httpx" if HAS_HTTPX else "urllib",
                    "total_requests": _TOTAL_REQUESTS,
                    "auth": get_auth_details(),
                    "models": list(MODELS.keys())
                }
                self.send_json(status_payload)
                return

            # Auth Status endpoint
            if self.path in ("/v1/auth/status", "/api/auth/status"):
                self.send_json(get_auth_details())
                return

            # API Logs endpoint
            if self.path == "/api/logs":
                with _LOGS_LOCK:
                    self.send_json(_REQUEST_LOGS)
                return

            if self.path.startswith("/v1") and not self._authorized():
                self.send_json({"error": {"message": "invalid api key"}}, 401)
                _record_request_log(client_ip, "GET", self.path, None, 401, 0, "Unauthorized")
                return
            if self.path == "/v1/models":
                self.send_json({"object": "list", "data": [
                    {"id": n, "object": "model", "created": 1700000000,
                     "owned_by": "google", "description": c["desc"]}
                    for n, c in MODELS.items()
                ]})
            elif self.path.startswith("/v1beta/models"):
                self.send_json({"models": [
                    {"name": f"models/{n}", "displayName": n, "description": c["desc"],
                     "supportedGenerationMethods": ["generateContent", "streamGenerateContent"]}
                    for n, c in MODELS.items()
                ]})
            elif self.path == "/":
                self.send_json({
                    "status": "ok",
                    "version": __version__,
                    "dashboard": "/dash",
                    "models": list(MODELS.keys()),
                    "auth": get_auth_details()
                })
            else:
                self.send_json({"error": "not found"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        client_ip = self.client_address[0] if self.client_address else "-"
        start_t = time.time()
        try:
            body = self._read_request_body()

            # Auth Sync Endpoint
            if self.path in ("/v1/auth/sync", "/api/auth/sync"):
                self._handle_auth_sync(body)
                return

            # Auth Logout Endpoint
            if self.path in ("/v1/auth/logout", "/api/auth/logout"):
                self._handle_auth_logout()
                return

            # Config Update Endpoint
            if self.path == "/api/config":
                self._handle_config_update(body)
                return

            # Auto-Login Trigger Endpoint
            if self.path == "/api/auth/login":
                self._handle_trigger_login()
                return


            if self.path.startswith("/v1") and not self._authorized():
                self.send_json({"error": {"message": "invalid api key"}}, 401)
                _record_request_log(client_ip, "POST", self.path, None, 401, int((time.time() - start_t) * 1000), "Unauthorized")
                return

            if self.path == "/v1/chat/completions":
                self._handle_chat(body)
            elif self.path == "/v1/responses":
                self._handle_responses(body)
            elif ":streamGenerateContent" in self.path:
                self._handle_google_generate(body, stream=True)
            elif ":generateContent" in self.path:
                self._handle_google_generate(body, stream=False)
            else:
                self.send_json({"error": "not found"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            log(f"POST error: {e}")
            try:
                self.send_json({"error": {"message": str(e)}}, 500)
            except:
                pass

    def _handle_auth_sync(self, body: bytes):
        """Handle incoming credentials sync from browser extension, dashboard or CLI."""
        req = self._parse_body(body)
        if not req:
            self.send_json({"error": {"message": "invalid JSON body"}}, 400)
            return

        cookie_str = req.get("cookie", "")
        sapisid = req.get("sapisid", "")
        xsrf_token = req.get("xsrf_token")
        auth_user = req.get("auth_user")
        gemini_bl = req.get("gemini_bl")
        account_name = req.get("account_name")
        account_email = req.get("account_email")
        account_photo = req.get("account_photo")

        if not cookie_str and not sapisid:
            self.send_json({"error": {"message": "cookie or sapisid is required"}}, 400)
            return

        auth_payload = {
            "cookie": cookie_str,
            "sapisid": sapisid,
            "auth_user": auth_user,
            "xsrf_token": xsrf_token,
            "gemini_bl": gemini_bl,
            "account_name": account_name,
            "account_email": account_email,
            "account_photo": account_photo
        }

        # Save to both local directory and global persistent user config directory
        save_paths = [
            os.path.abspath("gemini-auth.json"),
            get_default_auth_path()
        ]
        for p in save_paths:
            try:
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, "w") as f:
                    json.dump(auth_payload, f, indent=2)
            except Exception as e:
                log(f"Error saving {p}: {e}")

        # Update in-memory config
        CONFIG["cookie_file"] = save_paths[0]
        if xsrf_token:
            CONFIG["xsrf_token"] = xsrf_token
        if auth_user is not None:
            CONFIG["auth_user"] = auth_user
        if gemini_bl:
            CONFIG["gemini_bl"] = gemini_bl
        if account_name is not None:
            CONFIG["account_name"] = account_name
        if account_email is not None:
            CONFIG["account_email"] = account_email
        if account_photo is not None:
            CONFIG["account_photo"] = account_photo

        # Persist to config.json in all standard locations
        for cfg_p in ["./config.json", os.path.expanduser("~/.config/gemini-web2api/config.json")]:
            if os.path.exists(cfg_p):
                try:
                    with open(cfg_p, "r") as f:
                        cfg_data = json.load(f)
                    cfg_data["cookie_file"] = save_paths[0]
                    if xsrf_token:
                        cfg_data["xsrf_token"] = xsrf_token
                    if auth_user is not None:
                        cfg_data["auth_user"] = auth_user
                    if gemini_bl:
                        cfg_data["gemini_bl"] = gemini_bl
                    if account_name is not None:
                        cfg_data["account_name"] = account_name
                    if account_email is not None:
                        cfg_data["account_email"] = account_email
                    with open(cfg_p, "w") as f:
                        json.dump(cfg_data, f, indent=2)
                except Exception as e:
                    log(f"Error updating {cfg_p}: {e}")

        log("Successfully synced authentication session.")
        self.send_json({
            "status": "ok",
            "message": "Authentication synced successfully",
            "auth": get_auth_details()
        })

    def _handle_auth_logout(self):
        """Clear active authentication session and reset to anonymous mode."""
        clear_auth()

        # Remove or clear gemini-auth.json and cookie.txt across local and global locations
        clean_paths = [
            "gemini-auth.json",
            "cookie.txt",
            get_default_auth_path(),
            os.path.expanduser("~/.config/gemini-web2api/cookie.txt"),
        ]
        for p in clean_paths:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception as e:
                    log(f"Error removing {p}: {e}")

        # Update config.json in all standard locations
        for cfg_p in ["./config.json", os.path.expanduser("~/.config/gemini-web2api/config.json")]:
            if os.path.exists(cfg_p):
                try:
                    with open(cfg_p, "r") as f:
                        cfg_data = json.load(f)
                    cfg_data["cookie_file"] = None
                    cfg_data["xsrf_token"] = None
                    cfg_data["auth_user"] = None
                    cfg_data["account_name"] = None
                    cfg_data["account_email"] = None
                    with open(cfg_p, "w") as f:
                        json.dump(cfg_data, f, indent=2)
                except Exception as e:
                    log(f"Error updating {cfg_p}: {e}")

        log("Successfully logged out and cleared session.")
        self.send_json({
            "status": "ok",
            "message": "Logged out successfully. Server reset to Anonymous mode.",
            "auth": get_auth_details()
        })


    def _handle_config_update(self, body: bytes):
        """Update server configuration at runtime."""
        req = self._parse_body(body)
        if not req:
            self.send_json({"error": {"message": "invalid JSON"}}, 400)
            return

        for k in ("default_model", "proxy", "temporary_chats", "api_keys"):
            if k in req:
                CONFIG[k] = req[k]

        cfg_path = find_config() or "./config.json"
        try:
            cfg_data = dict(CONFIG)
            with open(cfg_path, "w") as f:
                json.dump(cfg_data, f, indent=2)
        except Exception as e:
            log(f"Error saving config: {e}")

        self.send_json({"status": "ok", "config": CONFIG})

    def _handle_trigger_login(self):
        """Launch the automated login tool in a background thread."""
        def _bg_run():
            try:
                from .login import launch_login_automation
                launch_login_automation()
            except Exception as e:
                log(f"Background login launch error: {e}")

        t = threading.Thread(target=_bg_run, daemon=True)
        t.start()
        self.send_json({
            "status": "ok",
            "message": "Automated login helper launched in background! Please check the opened browser window to log in."
        })


    # ─── /v1/chat/completions ─────────────────────────────────────────────────

    def _handle_chat(self, body: bytes):
        req = self._parse_body(body)
        if req is None:
            self.send_json({"error": {"message": "invalid JSON"}}, 400)
            return
        model_name, model_id, think_mode, err, extra_fields = resolve_model(
            req.get("model", CONFIG["default_model"]))
        if err:
            self.send_json({"error": {"message": err}}, 400)
            return

        tools = req.get("tools")
        tool_choice = req.get("tool_choice", "auto")
        prompt, images = messages_to_prompt(req.get("messages", []), tools, tool_choice)
        if not prompt.strip():
            self.send_json({"error": {"message": "empty prompt"}}, 400)
            return

        stream = req.get("stream", False)
        cid = f"chatcmpl-{uuid.uuid4().hex[:12]}"
        try:
            file_refs = _upload_images(images)
        except RuntimeError as e:
            self.send_json({"error": {"message": f"upstream error: {e}"}}, 502)
            return

        if stream and (not tools or tool_choice == "none"):
            try:
                self._start_sse()
                first_chunk = {
                    "id": cid,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model_name,
                    "choices": [{
                        "index": 0,
                        "delta": {"role": "assistant"},
                        "finish_reason": None,
                    }],
                }
                self.wfile.write(f"data: {json.dumps(first_chunk)}\n\n".encode())
                self.wfile.flush()
                for delta in generate_stream(prompt, model_id, think_mode, file_refs, extra_fields):
                    chunk = {"id": cid, "object": "chat.completion.chunk", "created": int(time.time()),
                             "model": model_name, "choices": [{"index": 0, "delta": {"content": delta}, "finish_reason": None}]}
                    self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode())
                    self.wfile.flush()
                end = {"id": cid, "object": "chat.completion.chunk", "created": int(time.time()),
                       "model": model_name, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
                self.wfile.write(f"data: {json.dumps(end)}\n\n".encode())
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as e:
                log(f"Stream error: {e}")
            return

        try:
            text = generate(prompt, model_id, think_mode, file_refs, extra_fields)
        except Exception as e:
            self.send_json({"error": {"message": f"upstream error: {e}"}}, 502)
            return

        tool_calls = None
        if tools and text and tool_choice != "none":
            text, tool_calls = parse_tool_calls(text)
        msg = {"role": "assistant", "content": text or None}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        finish = "tool_calls" if tool_calls else "stop"

        if stream:
            self._start_sse()
            chunk = {"id": cid, "object": "chat.completion.chunk", "created": int(time.time()),
                     "model": model_name, "choices": [{"index": 0, "delta": msg, "finish_reason": finish}]}
            self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        else:
            self.send_json({
                "id": cid, "object": "chat.completion", "created": int(time.time()),
                "model": model_name,
                "choices": [{"index": 0, "message": msg, "finish_reason": finish}],
                "usage": {"prompt_tokens": len(prompt)//4, "completion_tokens": len(text or "")//4,
                          "total_tokens": (len(prompt)+len(text or ""))//4},
            })

    # ─── /v1/responses (Codex CLI) ───────────────────────────────────────────

    def _handle_responses(self, body: bytes):
        req = self._parse_body(body)
        if req is None:
            self.send_json({"error": {"message": "invalid JSON"}}, 400)
            return
        model_name, model_id, think_mode, err, extra_fields = resolve_model(
            req.get("model", CONFIG["default_model"]))
        if err:
            self.send_json({"error": {"message": err}}, 400)
            return

        input_items = req.get("input", [])
        tools = req.get("tools")
        messages = []
        if req.get("instructions"):
            messages.append({"role": "system", "content": req["instructions"]})
        if isinstance(input_items, str):
            messages.append({"role": "user", "content": input_items})
        elif isinstance(input_items, list):
            for item in input_items:
                if isinstance(item, str):
                    messages.append({"role": "user", "content": item})
                elif isinstance(item, dict):
                    if item.get("type") == "function_call_output":
                        messages.append({"role": "tool", "tool_call_id": item.get("call_id", ""),
                                         "name": item.get("name", ""), "content": item.get("output", "")})
                    elif item.get("type") in ("input_text", "input_image", "image"):
                        messages.append({"role": "user", "content": [item]})
                    elif item.get("role") == "assistant" or (item.get("type") == "message" and item.get("role") == "assistant"):
                        cp = item.get("content", [])
                        text_acc, tc_list = "", []
                        if isinstance(cp, list):
                            for c in cp:
                                if isinstance(c, dict):
                                    if c.get("type") == "output_text":
                                        text_acc += c.get("text", "")
                                    elif c.get("type") == "function_call":
                                        tc_list.append(c)
                        elif isinstance(cp, str):
                            text_acc = cp
                        m = {"role": "assistant", "content": text_acc or None}
                        if tc_list:
                            m["tool_calls"] = [{"id": tc.get("call_id", f"call_{i}"), "type": "function",
                                                "function": {"name": tc.get("name",""), "arguments": tc.get("arguments","{}")}}
                                               for i, tc in enumerate(tc_list)]
                        messages.append(m)
                    else:
                        role = item.get("role", "user")
                        messages.append({"role": role, "content": item.get("content", "")})

        if tools:
            tools = [{"type": "function", "function": {"name": t["name"], "description": t.get("description", ""), "parameters": t.get("parameters", {})}}
                     if t.get("type") == "function" and "function" not in t else t for t in tools]

        tool_choice = req.get("tool_choice", "auto")
        prompt, images = messages_to_prompt(messages, tools, tool_choice)
        if not prompt.strip():
            self.send_json({"error": {"message": "empty input"}}, 400)
            return

        try:
            file_refs = _upload_images(images)
            text = generate(prompt, model_id, think_mode, file_refs, extra_fields)
        except Exception as e:
            self.send_json({"error": {"message": f"upstream error: {e}"}}, 502)
            return

        tool_calls = None
        if tools and text and tool_choice != "none":
            text, tool_calls = parse_tool_calls(text)

        rid = f"resp_{uuid.uuid4().hex[:16]}"
        mid = f"msg_{uuid.uuid4().hex[:12]}"
        output = []
        if tool_calls:
            for tc in tool_calls:
                output.append({"type": "function_call", "id": tc["id"], "call_id": tc["id"],
                               "name": tc["function"]["name"], "arguments": tc["function"]["arguments"], "status": "completed"})
        if text or not tool_calls:
            output.append({"type": "message", "id": mid, "role": "assistant", "status": "completed",
                           "content": [{"type": "output_text", "text": text or "", "annotations": []}]})

        if req.get("stream"):
            self._start_sse()
            sequence_number = 0

            def emit(event_type, **fields):
                nonlocal sequence_number
                sequence_number += 1
                event = {
                    "type": event_type,
                    "sequence_number": sequence_number,
                    **fields,
                }
                self.wfile.write(
                    f"event: {event_type}\ndata: {json.dumps(event)}\n\n".encode()
                )

            usage = {
                "input_tokens": len(prompt) // 4,
                "output_tokens": len(text or "") // 4,
                "total_tokens": (len(prompt) + len(text or "")) // 4,
            }
            base_response = {
                "id": rid,
                "object": "response",
                "created_at": int(time.time()),
                "model": model_name,
            }
            emit(
                "response.created",
                response={
                    **base_response,
                    "status": "in_progress",
                    "output": [],
                    "usage": None,
                },
            )
            emit(
                "response.in_progress",
                response={
                    **base_response,
                    "status": "in_progress",
                    "output": [],
                    "usage": None,
                },
            )
            for output_index, item in enumerate(output):
                if item["type"] == "function_call":
                    pending_item = {
                        "type": "function_call",
                        "id": item["id"],
                        "call_id": item["call_id"],
                        "name": item["name"],
                        "arguments": "",
                        "status": "in_progress",
                    }
                    emit(
                        "response.output_item.added",
                        output_index=output_index,
                        item=pending_item,
                    )
                    emit(
                        "response.function_call_arguments.delta",
                        item_id=item["id"],
                        output_index=output_index,
                        delta=item["arguments"],
                    )
                    emit(
                        "response.function_call_arguments.done",
                        item_id=item["id"],
                        output_index=output_index,
                        arguments=item["arguments"],
                    )
                    emit(
                        "response.output_item.done",
                        output_index=output_index,
                        item=item,
                    )
                elif item["type"] == "message":
                    pending_item = {
                        "type": "message",
                        "id": item["id"],
                        "role": "assistant",
                        "status": "in_progress",
                        "content": [],
                    }
                    emit(
                        "response.output_item.added",
                        output_index=output_index,
                        item=pending_item,
                    )
                    for content_index, content_part in enumerate(item["content"]):
                        event_fields = {
                            "item_id": item["id"],
                            "output_index": output_index,
                            "content_index": content_index,
                        }
                        emit(
                            "response.content_part.added",
                            **event_fields,
                            part={
                                "type": "output_text",
                                "text": "",
                                "annotations": [],
                            },
                        )
                        emit(
                            "response.output_text.delta",
                            **event_fields,
                            delta=content_part["text"],
                        )
                        emit(
                            "response.output_text.done",
                            **event_fields,
                            text=content_part["text"],
                        )
                        emit(
                            "response.content_part.done",
                            **event_fields,
                            part=content_part,
                        )
                    emit(
                        "response.output_item.done",
                        output_index=output_index,
                        item=item,
                    )
            emit(
                "response.completed",
                response={
                    **base_response,
                    "status": "completed",
                    "output": output,
                    "usage": usage,
                },
            )
            self.wfile.flush()
        else:
            self.send_json({"id": rid, "object": "response", "created_at": int(time.time()), "status": "completed",
                            "model": model_name, "output": output,
                            "usage": {"input_tokens": len(prompt)//4, "output_tokens": len(text or "")//4, "total_tokens": (len(prompt)+len(text or ""))//4}})

    # ─── /v1beta/models (Google Gemini CLI) ──────────────────────────────────

    def _handle_google_generate(self, body: bytes, stream: bool):
        req = self._parse_body(body)
        if req is None:
            self.send_json({"error": {"message": "invalid JSON"}}, 400)
            return
        m = re.match(r'/v1beta/models/([^:?]+)', self.path)
        model_name = m.group(1) if m else CONFIG["default_model"]
        model_name, model_id, think_mode, err, extra_fields = resolve_model(model_name)
        if err:
            self.send_json({"error": {"message": err}}, 400)
            return

        tool_config = req.get("toolConfig", {})
        fc_mode = tool_config.get("functionCallingConfig", {}).get("mode", "AUTO")
        has_tools = bool(req.get("tools")) and fc_mode != "NONE"
        prompt, images = google_contents_to_prompt(req)
        if not prompt.strip():
            self.send_json({"error": {"message": "empty content"}}, 400)
            return

        try:
            file_refs = _upload_images(images)
        except RuntimeError as e:
            self.send_json({"error": {"message": f"upstream error: {e}"}}, 502)
            return
        log(f"Google API: model={model_name} stream={stream} tools={has_tools} prompt_len={len(prompt)}")

        if stream and not has_tools:
            try:
                self._start_sse()
                full_text = ""
                for delta in generate_stream(prompt, model_id, think_mode, file_refs, extra_fields):
                    if not delta:
                        continue
                    full_text += delta
                    chunk_obj = {
                        "candidates": [{"content": {"parts": [{"text": delta}], "role": "model"}, "index": 0}],
                        "modelVersion": model_name,
                    }
                    self.wfile.write(f"data: {json.dumps(chunk_obj, ensure_ascii=False)}\n\n".encode())
                    self.wfile.flush()
                final_chunk = {
                    "candidates": [{"finishReason": "STOP", "index": 0}],
                    "usageMetadata": {
                        "promptTokenCount": len(prompt) // 4,
                        "candidatesTokenCount": len(full_text) // 4,
                        "totalTokenCount": (len(prompt) + len(full_text)) // 4,
                    },
                    "modelVersion": model_name,
                }
                self.wfile.write(f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n".encode())
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as e:
                log(f"Google stream error: {e}")
            return

        try:
            text = generate(prompt, model_id, think_mode, file_refs, extra_fields)
        except Exception as e:
            self.send_json({"error": {"message": f"upstream error: {e}"}}, 502)
            return

        if not text:
            log("Warning: empty response from Gemini")

        response_parts = []
        if has_tools and text:
            clean_text, function_calls = parse_google_function_calls(text)
            if function_calls:
                if clean_text:
                    response_parts.append({"text": clean_text})
                for fc in function_calls:
                    response_parts.append({"functionCall": {"name": fc["name"], "args": fc["args"]}})
            else:
                response_parts.append({"text": text})
        else:
            response_parts.append({"text": text or "I apologize, but I was unable to generate a response. Please try again."})

        candidate = {
            "content": {"parts": response_parts, "role": "model"},
            "finishReason": "STOP",
            "index": 0,
        }
        usage = {
            "promptTokenCount": len(prompt) // 4,
            "candidatesTokenCount": len(text or "") // 4,
            "totalTokenCount": (len(prompt) + len(text or "")) // 4,
        }
        response_obj = {
            "candidates": [candidate],
            "usageMetadata": usage,
            "modelVersion": model_name,
        }

        if stream:
            self._start_sse()
            self.wfile.write(f"data: {json.dumps(response_obj, ensure_ascii=False)}\n\n".encode())
            self.wfile.flush()
        else:
            self.send_json(response_obj)


class ThreadedServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True
