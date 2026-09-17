"""Automated Google Gemini Web Login and Cookie Extraction Tool."""
import os
import sys
import json
import time
import shutil
import socket
import urllib.request
import urllib.parse
import subprocess
import argparse
import asyncio
from typing import Optional, Dict, Any, Tuple, List

EXPORT_ORDER = [
    "SID",
    "HSID",
    "SSID",
    "APISID",
    "SAPISID",
    "LSID",
    "OSID",
    "SIDCC",
    "AEC",
    "NID",
    "COMPASS",
    "__Secure-1PAPISID",
    "__Secure-1PSID",
    "__Secure-1PSIDTS",
    "__Secure-1PSIDCC",
    "__Secure-1PSIDRTS",
    "__Secure-3PAPISID",
    "__Secure-3PSID",
    "__Secure-3PSIDTS",
    "__Secure-3PSIDCC",
    "__Secure-3PSIDRTS",
    "__Secure-OSID",
    "__Host-1PLSID",
    "__Host-3PLSID",
]

CORE_REQUIRED = ["SAPISID"]
SESSION_ALTERNATIVES = ["__Secure-1PSID", "__Secure-3PSID", "SID"]


def find_browser_executable() -> Optional[str]:
    """Find installed Chromium-based browser executable across macOS, Linux, Windows."""
    # macOS
    if sys.platform == "darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Arc.app/Contents/MacOS/Arc",
            os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            os.path.expanduser("~/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"),
            os.path.expanduser("~/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
        ]
        for p in candidates:
            if os.path.exists(p) and os.access(p, os.X_OK):
                return p

    # Linux / Unix
    for name in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "brave-browser", "microsoft-edge"]:
        path = shutil.which(name)
        if path:
            return path

    # Windows
    if sys.platform == "win32":
        win_dirs = [
            os.environ.get("PROGRAMFILES", r"C:\Program Files"),
            os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
            os.environ.get("LOCALAPPDATA", ""),
        ]
        win_candidates = [
            r"Google\Chrome\Application\chrome.exe",
            r"Microsoft\Edge\Application\msedge.exe",
            r"BraveSoftware\Brave-Browser\Application\brave.exe",
        ]
        for base in win_dirs:
            if not base:
                continue
            for rel in win_candidates:
                full = os.path.join(base, rel)
                if os.path.exists(full):
                    return full

    return None


def get_default_profile_dir() -> str:
    """Return persistent browser profile directory."""
    base = os.path.expanduser("~/.config/gemini-web2api/browser_profile")
    os.makedirs(base, exist_ok=True)
    return base


def find_free_port() -> int:
    """Find an available TCP port for CDP."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def send_cdp_command(ws, method: str, params: dict = None, cmd_id: int = 1) -> dict:
    """Send a CDP command over WebSocket and return response."""
    payload = {"id": cmd_id, "method": method, "params": params or {}}
    await ws.send(json.dumps(payload))
    while True:
        raw = await ws.recv()
        data = json.loads(raw)
        if data.get("id") == cmd_id:
            return data


async def extract_session_via_cdp(cdp_port: int, max_wait_sec: int = 180) -> Optional[dict]:
    """Connect to Chrome via CDP and wait for Gemini session cookies + XSRF token."""
    try:
        import websockets
    except ImportError:
        print("[!] websockets library not found. Run: uv pip install websockets or pip install websockets")
        return None

    print(f"[*] Connecting to browser remote debugging port {cdp_port}...")
    start_time = time.time()
    tab_ws_url = None

    # Wait for CDP endpoint to be ready
    while time.time() - start_time < 30:
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{cdp_port}/json/list")
            with urllib.request.urlopen(req, timeout=2) as resp:
                tabs = json.loads(resp.read().decode())
                for tab in tabs:
                    if "gemini.google.com" in tab.get("url", ""):
                        tab_ws_url = tab.get("webSocketDebuggerUrl")
                        break
                if not tab_ws_url and tabs:
                    # Pick first page tab
                    for tab in tabs:
                        if tab.get("type") == "page":
                            tab_ws_url = tab.get("webSocketDebuggerUrl")
                            break
                if tab_ws_url:
                    break
        except Exception:
            await asyncio.sleep(0.5)

    if not tab_ws_url:
        print("[!] Could not connect to browser DevTools endpoint.")
        return None

    print("[*] Monitoring browser session... Please sign in to Google / Gemini in the opened browser window.")

    async with websockets.connect(tab_ws_url) as ws:
        cmd_id = 1

        # Enable Network and Runtime
        await send_cdp_command(ws, "Network.enable", {}, cmd_id=cmd_id)
        cmd_id += 1
        await send_cdp_command(ws, "Runtime.enable", {}, cmd_id=cmd_id)
        cmd_id += 1

        # Polling loop
        last_log = 0
        while time.time() - start_time < max_wait_sec:
            # 1. Fetch all cookies
            cookies_resp = await send_cdp_command(ws, "Network.getAllCookies", {}, cmd_id=cmd_id)
            cmd_id += 1

            raw_cookies = cookies_resp.get("result", {}).get("cookies", [])
            google_cookies = {}
            for c in raw_cookies:
                domain = c.get("domain", "").lower().lstrip(".")
                if domain == "google.com" or domain.endswith(".google.com"):
                    name = c.get("name")
                    val = c.get("value")
                    if name and val:
                        # Prefer .google.com or .gemini.google.com
                        google_cookies[name] = val

            has_sapisid = "SAPISID" in google_cookies
            has_session = any(k in google_cookies for k in SESSION_ALTERNATIVES)

            # 2. Evaluate page metadata
            eval_script = """
            (() => {
                const wiz = globalThis.WIZ_global_data || {};
                const html = document.documentElement ? document.documentElement.innerHTML : '';
                
                const regexValue = (name) => {
                    const patterns = [
                        new RegExp('"' + name + '"\\\\s*:\\\\s*"([^"\\\\n]+)"'),
                        new RegExp('\\\\\\\\"' + name + '\\\\\\\\"\\\\s*:\\\\s*\\\\\\\\"([^"\\\\n]+)\\\\\\\\"')
                    ];
                    for (const p of patterns) {
                        const m = html.match(p);
                        if (m && m[1]) return m[1];
                    }
                    return null;
                };

                let bl = wiz.cfb2h || regexValue('cfb2h');
                if (!bl) {
                    try {
                        const res = performance.getEntriesByType('resource');
                        for (const r of res) {
                            if (r.name && r.name.includes('gemini.google.com')) {
                                const url = new URL(r.name);
                                const qbl = url.searchParams.get('bl');
                                if (qbl) { bl = qbl; break; }
                            }
                        }
                    } catch(e) {}
                }

                const xsrf = wiz.SNlM0e || regexValue('SNlM0e');
                const path = window.location.pathname || '';
                const uMatch = path.match(/^\\/u\\/(\\d+)/);
                const authUser = uMatch ? uMatch[1] : null;

                // Extract account profile details
                let accountEmail = null;
                let accountName = null;
                let accountPhoto = null;

                const targets = document.querySelectorAll('a[aria-label*="@"], button[aria-label*="@"], a[aria-label*="Google Account"], button[aria-label*="Google Account"], a[href*="SignOutOptions"], a[href*="accounts.google.com"]');
                for (const el of targets) {
                    const label = el.getAttribute('aria-label') || el.getAttribute('title') || '';
                    const emMatch = label.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})/);
                    if (emMatch && !accountEmail) accountEmail = emMatch[1];

                    const nmMatch = label.match(/(?:Google Account:\\\\s*)?([^\\\\n(\\\\]]+?)(?:\\\\s*[\\\\n(]\\\\s*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}|\\\\s*$)/i);
                    if (nmMatch && nmMatch[1] && !accountName) {
                        const n = nmMatch[1].trim().replace(/^Google Account:\\\\s*/i, '');
                        if (n && !n.includes('@')) accountName = n;
                    }

                    const img = el.querySelector('img') || (el.tagName === 'IMG' ? el : null);
                    if (img && img.src && img.src.includes('googleusercontent.com') && !accountPhoto) {
                        accountPhoto = img.src;
                    }
                }

                if (!accountPhoto) {
                    const img = document.querySelector('img[src*="googleusercontent.com/a/"], img[src*="googleusercontent.com/ogw/"]');
                    if (img && img.src) accountPhoto = img.src;
                }

                try {
                    const str = JSON.stringify(wiz);
                    if (!accountEmail) {
                        const em = str.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})/);
                        if (em) accountEmail = em[1];
                    }
                } catch(e) {}

                return {
                    xsrf_token: xsrf,
                    gemini_bl: bl,
                    auth_user: authUser,
                    account_name: accountName,
                    account_email: accountEmail,
                    account_photo: accountPhoto,
                    url: window.location.href
                };
            })()
            """
            eval_resp = await send_cdp_command(ws, "Runtime.evaluate", {"expression": eval_script, "returnByValue": True}, cmd_id=cmd_id)
            cmd_id += 1

            page_data = eval_resp.get("result", {}).get("result", {}).get("value", {})
            xsrf_token = page_data.get("xsrf_token")
            gemini_bl = page_data.get("gemini_bl")
            auth_user = page_data.get("auth_user")
            account_name = page_data.get("account_name")
            account_email = page_data.get("account_email")
            account_photo = page_data.get("account_photo")
            current_url = page_data.get("url", "")

            # Check if we have complete credentials
            if has_sapisid and has_session and xsrf_token:
                cookie_str = "; ".join(f"{k}={google_cookies[k]}" for k in EXPORT_ORDER if k in google_cookies)
                return {
                    "cookie": cookie_str,
                    "sapisid": google_cookies["SAPISID"],
                    "auth_user": auth_user,
                    "xsrf_token": xsrf_token,
                    "gemini_bl": gemini_bl,
                    "account_name": account_name,
                    "account_email": account_email,
                    "account_photo": account_photo,
                    "cookie_count": len([k for k in EXPORT_ORDER if k in google_cookies])
                }

            if time.time() - last_log > 5:
                status_parts = []
                status_parts.append(f"Cookies: {'✓' if has_sapisid and has_session else '...'}")
                status_parts.append(f"XSRF (SNlM0e): {'✓' if xsrf_token else '...'}")
                if current_url:
                    status_parts.append(f"URL: {current_url[:40]}...")
                print(f"[*] Waiting for login... [{', '.join(status_parts)}]")
                last_log = time.time()

            await asyncio.sleep(1.5)

    return None


def run_login_flow(
    browser_path: Optional[str] = None,
    profile_dir: Optional[str] = None,
    output_file: str = "gemini-auth.json",
    sync_url: str = "http://127.0.0.1:8081",
    headless: bool = False,
    timeout_sec: int = 180
) -> bool:
    """Execute complete web login flow and extract cookies."""
    browser_exe = browser_path or find_browser_executable()
    if not browser_exe:
        print("[!] No Chromium-based browser (Chrome, Brave, Edge, Chromium) found.")
        print("    Please install Google Chrome or Microsoft Edge, or specify --browser <path>")
        return False

    profile = profile_dir or get_default_profile_dir()
    cdp_port = find_free_port()

    print("=" * 65)
    print(" Google Gemini Web Login & Cookie Automation")
    print("=" * 65)
    print(f" Browser:      {browser_exe}")
    print(f" Profile Dir:  {profile}")
    print(f" Debug Port:   {cdp_port}")
    print(f" Target URL:   https://gemini.google.com/app")
    print("=" * 65)

    cmd = [
        browser_exe,
        f"--remote-debugging-port={cdp_port}",
        f"--user-data-dir={profile}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-blink-features=AutomationControlled",
        "https://gemini.google.com/app",
    ]
    if headless:
        cmd.append("--headless=new")

    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        auth_data = asyncio.run(extract_session_via_cdp(cdp_port, max_wait_sec=timeout_sec))
        if not auth_data:
            print("[!] Failed to capture complete Gemini credentials within the timeout period.")
            return False

        # Write to output file and persistent global user config
        auth_file_path = os.path.abspath(output_file)
        global_auth_path = os.path.expanduser("~/.config/gemini-web2api/gemini-auth.json")
        os.makedirs(os.path.dirname(global_auth_path), exist_ok=True)

        for p in set([auth_file_path, global_auth_path]):
            try:
                with open(p, "w") as f:
                    json.dump(auth_data, f, indent=2)
            except Exception as e:
                print(f"[!] Warning: Could not write {p}: {e}")

        # Also write cookie.txt for compatibility in both locations
        cookie_text_paths = [
            os.path.abspath("cookie.txt"),
            os.path.expanduser("~/.config/gemini-web2api/cookie.txt")
        ]
        for cp in cookie_text_paths:
            try:
                with open(cp, "w") as f:
                    f.write(auth_data["cookie"] + "\n")
            except Exception:
                pass

        print("\n" + "=" * 65)
        print(" ✅ AUTHENTICATION SUCCESSFUL!")
        print("=" * 65)
        if auth_data.get("account_email") or auth_data.get("account_name"):
            acc_str = f"{auth_data.get('account_name') or ''} <{auth_data.get('account_email') or ''}>".strip()
            print(f" Google Account:     {acc_str}")
        print(f" Saved auth file:    {auth_file_path}")
        print(f" Global config auth: {global_auth_path}")
        print(f" Google Cookies:     {auth_data.get('cookie_count', 0)} captured")
        print(f" SAPISID:            Present")
        print(f" XSRF (SNlM0e):      {auth_data.get('xsrf_token')[:16]}...")
        print(f" Gemini BL (cfb2h):  {auth_data.get('gemini_bl') or 'Default'}")
        print(f" Auth User Index:    {auth_data.get('auth_user') or '0 (default)'}")
        print("=" * 65)

        # Update config.json if it exists in local or global paths
        for cfg_p in ["./config.json", os.path.expanduser("~/.config/gemini-web2api/config.json")]:
            if os.path.exists(cfg_p):
                try:
                    with open(cfg_p, "r") as f:
                        cfg = json.load(f)
                    cfg["cookie_file"] = auth_file_path
                    if auth_data.get("xsrf_token"):
                        cfg["xsrf_token"] = auth_data["xsrf_token"]
                    if auth_data.get("auth_user") is not None:
                        cfg["auth_user"] = auth_data["auth_user"]
                    if auth_data.get("gemini_bl"):
                        cfg["gemini_bl"] = auth_data["gemini_bl"]
                    if auth_data.get("account_name"):
                        cfg["account_name"] = auth_data["account_name"]
                    if auth_data.get("account_email"):
                        cfg["account_email"] = auth_data["account_email"]
                    with open(cfg_p, "w") as f:
                        json.dump(cfg, f, indent=2)
                    print(f" [*] Automatically updated {cfg_p}")
                except Exception as e:
                    print(f" [!] Could not update {cfg_p}: {e}")

        # Try to sync to active running server if reachable
        if sync_url:
            try:
                sync_endpoint = f"{sync_url.rstrip('/')}/v1/auth/sync"
                req = urllib.request.Request(
                    sync_endpoint,
                    data=json.dumps(auth_data).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=3) as resp:
                    if resp.status == 200:
                        print(f" [*] Successfully hot-synced credentials with running server at {sync_url}")
            except Exception:
                pass

        return True
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def check_auth_status(auth_file: str = "gemini-auth.json") -> dict:
    """Validate existing auth file without opening browser with auto-discovery."""
    target_file = auth_file
    if not os.path.exists(target_file):
        # Auto-discover in standard locations
        global_p = os.path.expanduser("~/.config/gemini-web2api/gemini-auth.json")
        if os.path.exists(global_p):
            target_file = global_p
        else:
            print(f"[!] Auth file '{auth_file}' not found.")
            return {"valid": False, "error": "file not found"}

    try:
        with open(target_file, "r") as f:
            data = json.load(f)
        cookie_str = data.get("cookie", "")
        sapisid = data.get("sapisid", "")
        xsrf = data.get("xsrf_token", "")
        auth_user = data.get("auth_user")
        gemini_bl = data.get("gemini_bl")

        valid = bool(cookie_str and sapisid and xsrf)
        print("=" * 55)
        print(" Gemini Auth Status Check")
        print("=" * 55)
        print(f" File:         {os.path.abspath(target_file)}")
        if data.get("account_name") or data.get("account_email"):
            print(f" Account:      {data.get('account_name') or ''} <{data.get('account_email') or ''}>".strip())
        print(f" Cookie:       {'✓ Present' if cookie_str else '✗ Missing'}")
        print(f" SAPISID:      {'✓ Present' if sapisid else '✗ Missing'}")
        print(f" XSRF Token:   {'✓ Present' if xsrf else '✗ Missing'}")
        print(f" Gemini BL:    {gemini_bl or 'None'}")
        print(f" Auth User:    {auth_user if auth_user is not None else 'Default (0)'}")
        print(f" Pro Ready:    {'YES' if valid else 'NO'}")
        print("=" * 55)
        return {"valid": valid, "data": data}
    except Exception as e:
        print(f"[!] Error reading auth file: {e}")
        return {"valid": False, "error": str(e)}


def launch_login_automation():
    """Helper to launch login automation in background or from dashboard."""
    run_login_flow()


def main():
    parser = argparse.ArgumentParser(description="Automated Google Gemini Web Login & Cookie Sync")
    parser.add_argument("--browser", type=str, default=None, help="Path to browser executable")
    parser.add_argument("--profile-dir", type=str, default=None, help="Custom browser profile directory")
    parser.add_argument("--output", type=str, default="gemini-auth.json", help="Output auth JSON file path")
    parser.add_argument("--sync-url", type=str, default="http://127.0.0.1:8081", help="URL of running gemini-web2api server to sync with")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode (if already logged in)")
    parser.add_argument("--check", action="store_true", help="Check existing auth file validity")
    parser.add_argument("--timeout", type=int, default=180, help="Max seconds to wait for login")

    args = parser.parse_args()

    if args.check:
        res = check_auth_status(args.output)
        sys.exit(0 if res.get("valid") else 1)

    success = run_login_flow(
        browser_path=args.browser,
        profile_dir=args.profile_dir,
        output_file=args.output,
        sync_url=args.sync_url,
        headless=args.headless,
        timeout_sec=args.timeout
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
