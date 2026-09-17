"""Configuration management."""
import json
import os

DEFAULT_CONFIG = {
    "port": 8081,
    "host": "0.0.0.0",
    "retry_attempts": 3,
    "retry_delay_sec": 2,
    "request_timeout_sec": 180,
    "gemini_bl": "boq_assistant-bard-web-server_20260716.08_p0",
    "auth_user": None,
    "xsrf_token": None,
    "default_model": "gemini-3.6-flash",
    "log_requests": True,
    "cookie_file": None,
    "proxy": None,
    "api_keys": [],
    "temporary_chats": False,
    "account_name": None,
    "account_email": None,
    "account_photo": None,
}

CONFIG = dict(DEFAULT_CONFIG)


def get_global_config_dir() -> str:
    """Return persistent global configuration directory."""
    base = os.path.expanduser("~/.config/gemini-web2api")
    os.makedirs(base, exist_ok=True)
    return base


def get_default_auth_path() -> str:
    """Return default persistent global auth file path."""
    return os.path.join(get_global_config_dir(), "gemini-auth.json")


def get_browser_profile_dir() -> str:
    """Return persistent browser profile directory."""
    path = os.path.join(get_global_config_dir(), "browser_profile")
    os.makedirs(path, exist_ok=True)
    return path


def find_auth_file():
    """Find persistent auth file across explicit configs, local directory, and global config."""
    # 1. Explicitly configured file
    if CONFIG.get("cookie_file") and os.path.exists(CONFIG["cookie_file"]):
        return CONFIG["cookie_file"]
    # 2. Local workspace override
    if os.path.exists("./gemini-auth.json"):
        return os.path.abspath("./gemini-auth.json")
    # 3. Global persistent user config
    global_path = os.path.expanduser("~/.config/gemini-web2api/gemini-auth.json")
    if os.path.exists(global_path):
        return global_path
    # 4. Local cookie.txt
    if os.path.exists("./cookie.txt"):
        return os.path.abspath("./cookie.txt")
    # 5. Global cookie.txt
    global_cookie = os.path.expanduser("~/.config/gemini-web2api/cookie.txt")
    if os.path.exists(global_cookie):
        return global_cookie
    return None


def load_config(path: str = None):
    """Load config from JSON file and automatically discover persistent auth."""
    if path and os.path.exists(path):
        with open(path) as f:
            CONFIG.update(json.load(f))
    
    # Auto-resolve persistent auth file if not set or missing
    if not CONFIG.get("cookie_file") or not os.path.exists(CONFIG["cookie_file"]):
        auth_p = find_auth_file()
        if auth_p:
            CONFIG["cookie_file"] = auth_p
    return CONFIG


def find_config():
    """Search for config file in standard locations."""
    for p in ["./config.json", os.path.expanduser("~/.config/gemini-web2api/config.json")]:
        if os.path.exists(p):
            return p
    return None
