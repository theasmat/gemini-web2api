import os
import json
import time
import tempfile
import threading
import http.client
import unittest

from gemini_web2api.config import CONFIG, DEFAULT_CONFIG
from gemini_web2api.gemini import load_cookie, get_auth_details, _cookie_cache
from gemini_web2api.dashboard import render_dashboard
from gemini_web2api.server import GeminiHandler, ThreadedServer
from gemini_web2api.login import check_auth_status, find_browser_executable, find_free_port


class DashboardAndAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = find_free_port()
        cls.server = ThreadedServer(("127.0.0.1", cls.port), GeminiHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.original_config = dict(CONFIG)
        _cookie_cache.clear()
        _cookie_cache.update({"str": "", "sapisid": None, "mtime": 0})

    def tearDown(self):
        CONFIG.clear()
        CONFIG.update(self.original_config)
        _cookie_cache.clear()
        _cookie_cache.update({"str": "", "sapisid": None, "mtime": 0})
        # Clean test auth files
        for f in ["test-auth.json", "gemini-auth.json", "cookie.txt"]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass

    def _request(self, method: str, path: str, body: dict = None, headers: dict = None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        req_headers = headers or {}
        req_body = None
        if body is not None:
            req_body = json.dumps(body)
            req_headers["Content-Type"] = "application/json"
        conn.request(method, path, body=req_body, headers=req_headers)
        resp = conn.getresponse()
        data = resp.read()
        conn.close()
        return resp.status, resp.getheaders(), data

    def test_dashboard_html_rendering(self):
        html = render_dashboard()
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("Gemini Web2API Dashboard", html)
        self.assertIn("/v1/chat/completions", html)
        self.assertIn("API Playground", html)

    def test_get_dash_endpoint(self):
        status, headers, body = self._request("GET", "/dash")
        self.assertEqual(status, 200)
        self.assertTrue(any("text/html" in v for k, v in headers if k.lower() == "content-type"))
        self.assertIn(b"Gemini Web2API", body)

    def test_get_api_status(self):
        status, headers, body = self._request("GET", "/api/status")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data["status"], "ok")
        self.assertIn("auth", data)
        self.assertIn("models", data)
        self.assertIn("uptime_sec", data)

    def test_get_auth_status(self):
        status, headers, body = self._request("GET", "/v1/auth/status")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertIn("authenticated", data)
        self.assertIn("has_cookie", data)
        self.assertIn("pro_ready", data)

    def test_post_auth_sync(self):
        payload = {
            "cookie": "SID=abc12345; SAPISID=xyz98765; __Secure-1PSID=sec111",
            "sapisid": "xyz98765",
            "xsrf_token": "AOOh0P_test_token",
            "auth_user": "1",
            "gemini_bl": "boq_test_bl",
            "account_name": "Test User",
            "account_email": "test.user@gmail.com",
            "account_photo": "https://lh3.googleusercontent.com/a/test_avatar"
        }
        status, headers, body = self._request("POST", "/v1/auth/sync", body=payload)
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["auth"]["has_sapisid"], True)
        self.assertEqual(data["auth"]["has_xsrf"], True)
        self.assertEqual(data["auth"]["account_name"], "Test User")
        self.assertEqual(data["auth"]["account_email"], "test.user@gmail.com")
        self.assertEqual(CONFIG["xsrf_token"], "AOOh0P_test_token")
        self.assertEqual(CONFIG["auth_user"], "1")
        self.assertEqual(CONFIG["gemini_bl"], "boq_test_bl")
        self.assertEqual(CONFIG["account_name"], "Test User")
        self.assertEqual(CONFIG["account_email"], "test.user@gmail.com")

    def test_post_config_update(self):
        payload = {
            "default_model": "gemini-3.5-flash-thinking",
            "temporary_chats": True,
            "api_keys": ["sk-test-key-123"]
        }
        status, headers, body = self._request("POST", "/api/config", body=payload)
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(CONFIG["default_model"], "gemini-3.5-flash-thinking")
        self.assertEqual(CONFIG["temporary_chats"], True)
        self.assertEqual(CONFIG["api_keys"], ["sk-test-key-123"])

    def test_dynamic_cookie_reload_from_json(self):
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f:
            auth_json = {
                "cookie": "SAPISID=dynamic_sapisid; __Secure-1PSID=dyn_psid",
                "sapisid": "dynamic_sapisid",
                "xsrf_token": "dyn_xsrf_token",
                "auth_user": "2",
                "gemini_bl": "dyn_bl",
                "account_name": "Dynamic User",
                "account_email": "dynamic@gmail.com"
            }
            json.dump(auth_json, f)
            temp_path = f.name

        try:
            CONFIG["cookie_file"] = temp_path
            cookie_str, sapisid = load_cookie()
            self.assertEqual(sapisid, "dynamic_sapisid")
            self.assertIn("SAPISID=dynamic_sapisid", cookie_str)
            self.assertEqual(CONFIG["xsrf_token"], "dyn_xsrf_token")
            self.assertEqual(CONFIG["auth_user"], "2")
            self.assertEqual(CONFIG["gemini_bl"], "dyn_bl")
            self.assertEqual(CONFIG["account_name"], "Dynamic User")
            self.assertEqual(CONFIG["account_email"], "dynamic@gmail.com")

            details = get_auth_details()
            self.assertEqual(details["authenticated"], True)
            self.assertEqual(details["has_xsrf"], True)
            self.assertEqual(details["auth_user"], "2")
            self.assertEqual(details["account_name"], "Dynamic User")
            self.assertEqual(details["account_email"], "dynamic@gmail.com")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_check_auth_status_file(self):
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f:
            json.dump({
                "cookie": "SAPISID=test; __Secure-1PSID=test",
                "sapisid": "test",
                "xsrf_token": "test_xsrf",
                "auth_user": "0"
            }, f)
            temp_path = f.name

        try:
            res = check_auth_status(temp_path)
            self.assertTrue(res.get("valid"))
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
