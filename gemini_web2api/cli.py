"""Unified Interactive CLI & Command Runner for Gemini Web2API."""
import sys
import os
import json
import time
import argparse
import webbrowser

from . import __version__
from .config import CONFIG, load_config, find_config
from .models import MODELS
from .gemini import get_auth_details, clear_auth
from .server import GeminiHandler, ThreadedServer


# Terminal styling
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_header():
    auth = get_auth_details()
    auth_label = f"{GREEN}● Authenticated (Pro Ready){RESET}" if auth.get("pro_ready") else (
        f"{GREEN}● Authenticated (Standard){RESET}" if auth.get("authenticated") else f"{CYAN}○ Anonymous Mode{RESET}"
    )

    banner = (
        f"{BOLD}{MAGENTA}" + r"   ____ _____ __  __ ___ _   _ ___   __        _______ ____ ____    _    ____ ___ " + f"\n"
        f"{BOLD}{MAGENTA}" + r"  / ___| ____|  \/  |_ _| \ | |_ _|  \ \      / / ____| __ )___ \  / \  |  _ \_ _|" + f"\n"
        f"{BOLD}{CYAN}" + r" | |  _|  _| | |\/| || ||  \| || |____\ \ /\ / /|  _| |  _ \ __) |/ _ \ | |_) | | " + f"\n"
        f"{BOLD}{CYAN}" + r" | |_| | |___| |  | || || |\  || |_____\ V  V / | |___| |_) / __// ___ \|  __/| | " + f"\n"
        f"{BOLD}{BLUE}" + r"  \____|_____|_|  |_|___|_| \_|___|     \_/\_/  |_____|____/_____/_/   \_\_|  |___|" + f"{RESET}"
    )
    print()
    print(banner)
    print(f"                                                             {DIM}v{__version__}{RESET}")
    print(f"  {DIM}Status:{RESET}  {auth_label}")
    print(f"  {DIM}Config:{RESET}  Port: {CONFIG.get('port', 8081)} | Default Model: {CONFIG.get('default_model', 'gemini-3.6-flash')}")
    print(f"{DIM}{'─' * 76}{RESET}")



def cmd_status(args=None):
    """Print current server and authentication diagnostics."""
    config_path = find_config()
    if config_path:
        load_config(config_path)

    auth = get_auth_details()
    print(f"\n{BOLD}{CYAN}=== Gemini Web2API Status ==={RESET}")
    print(f"  Version:         {__version__}")
    print(f"  Config File:     {config_path or 'None (using defaults)'}")
    print(f"  Listening Port:  {CONFIG.get('port', 8081)}")
    print(f"  Default Model:   {CONFIG.get('default_model', 'gemini-3.6-flash')}")
    print(f"  Proxy:           {CONFIG.get('proxy') or 'None'}")
    print(f"  Temporary Chats: {'Enabled' if CONFIG.get('temporary_chats') else 'Disabled'}")
    print()
    print(f"{BOLD}Authentication:{RESET}")
    print(f"  Session State:   {'AUTHENTICATED' if auth.get('authenticated') else 'ANONYMOUS'}")
    print(f"  Cookie File:     {auth.get('cookie_file') or 'None'}")
    print(f"  Cookie Count:    {auth.get('cookie_count', 0)}")
    print(f"  SAPISID:         {'✓ Present' if auth.get('has_sapisid') else '✗ Missing'}")
    print(f"  XSRF Token:      {'✓ Present' if auth.get('has_xsrf') else '✗ Missing'}")
    print(f"  Auth User Index: {auth.get('auth_user') if auth.get('auth_user') is not None else 'Default (0)'}")
    print(f"  Pro Routing:     {'✓ ACTIVE (Pro models supported)' if auth.get('pro_ready') else '✗ Inactive (routes to Flash)'}")
    print()


def cmd_start(args=None):
    """Start HTTP proxy server."""
    port = getattr(args, "port", None) or CONFIG.get("port", 8081)
    open_dash = getattr(args, "open", False)

    server = ThreadedServer((CONFIG["host"], port), GeminiHandler)
    dash_url = f"http://localhost:{port}/dash"
    base_url = f"http://localhost:{port}/v1"

    print(f"\n{BOLD}{GREEN}✓ gemini-web2api server started!{RESET}")
    print(f"  {BOLD}Dashboard:{RESET} {CYAN}{dash_url}{RESET}")
    print(f"  {BOLD}Base URL:{RESET}  {CYAN}{base_url}{RESET}")
    print(f"  {DIM}Press Ctrl+C to stop.{RESET}\n")

    if open_dash:
        try:
            webbrowser.open(dash_url)
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n{DIM}Server stopped.{RESET}")
        server.shutdown()


def cmd_login(args=None):
    """Launch automated Google Gemini login."""
    from .login import run_login_flow
    browser = getattr(args, "browser", None)
    profile_dir = getattr(args, "profile_dir", None)
    headless = getattr(args, "headless", False)
    run_login_flow(browser_path=browser, profile_dir=profile_dir, headless=headless)


def cmd_logout(args=None):
    """Clear active session and reset to anonymous mode."""
    clear_auth()
    for p in ["gemini-auth.json", "cookie.txt"]:
        if os.path.exists(p):
            try:
                os.remove(p)
            except:
                pass
    cfg_path = find_config()
    if cfg_path and os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r") as f:
                cfg_data = json.load(f)
            cfg_data["cookie_file"] = None
            cfg_data["xsrf_token"] = None
            cfg_data["auth_user"] = None
            with open(cfg_path, "w") as f:
                json.dump(cfg_data, f, indent=2)
        except:
            pass
    print(f"\n{GREEN}✓ Logged out successfully. Server reset to Anonymous mode.{RESET}\n")


def cmd_chat(args=None):
    """Run interactive terminal chat REPL."""
    from .chat import run_chat_repl
    model = getattr(args, "model", "gemini-3.5-flash-thinking")
    run_chat_repl(model)


def cmd_client(args=None):
    """Print quick client configuration snippets."""
    port = CONFIG.get("port", 8081)
    print(f"\n{BOLD}{CYAN}=== Client Configuration Snippets ==={RESET}\n")
    print(f"{BOLD}1. Cherry Studio / ChatBox / NextChat / Any OpenAI Client:{RESET}")
    print(f"   API Type:      OpenAI")
    print(f"   Base URL:      http://localhost:{port}/v1")
    print(f"   API Key:       sk-gemini (or any string)")
    print(f"   Models:        gemini-3.5-flash-thinking, gemini-3.1-pro, gemini-3.6-flash\n")

    print(f"{BOLD}2. OpenAI Python SDK:{RESET}")
    print(f"""   from openai import OpenAI
   client = OpenAI(base_url="http://localhost:{port}/v1", api_key="sk-gemini")
   resp = client.chat.completions.create(
       model="gemini-3.5-flash-thinking",
       messages=[{{"role": "user", "content": "Hello!"}}]
   )
   print(resp.choices[0].message.content)\n""")

    print(f"{BOLD}3. curl (Terminal):{RESET}")
    print(f"""   curl http://localhost:{port}/v1/chat/completions \\
     -H "Content-Type: application/json" \\
     -H "Authorization: Bearer sk-gemini" \\
     -d '{{"model":"gemini-3.5-flash-thinking","messages":[{{"role":"user","content":"Hello!"}}]}}'\n""")


def cmd_config(args=None):
    """Interactive or argument-based config manager."""
    cfg_path = find_config() or "./config.json"
    if os.path.exists(cfg_path):
        load_config(cfg_path)

    if getattr(args, "port", None):
        CONFIG["port"] = args.port
    if getattr(args, "proxy", None):
        CONFIG["proxy"] = args.proxy
    if getattr(args, "model", None):
        CONFIG["default_model"] = args.model

    try:
        with open(cfg_path, "w") as f:
            json.dump(CONFIG, f, indent=2)
        print(f"\n{GREEN}✓ Saved configuration to {cfg_path}{RESET}\n")
    except Exception as e:
        print(f"\n{YELLOW}[!] Could not save configuration: {e}{RESET}\n")


def interactive_menu():
    """Main interactive TUI menu loop."""
    config_path = find_config()
    if config_path:
        load_config(config_path)

    while True:
        print_header()
        print(f"  {BOLD}[1]{RESET} 🚀 {BOLD}Start Server & Open Dashboard{RESET}")
        print(f"  {BOLD}[2]{RESET} 🔑 {BOLD}Login to Google / Gemini{RESET} (Automated Cookie Extractor)")
        print(f"  {BOLD}[3]{RESET} 💬 {BOLD}Terminal Chat REPL{RESET} (Interactive Chat in Terminal)")
        print(f"  {BOLD}[4]{RESET} 🛡️ {BOLD}Check Auth & Health Status{RESET}")
        print(f"  {BOLD}[5]{RESET} 🚪 {BOLD}Logout / Reset to Anonymous{RESET}")
        print(f"  {BOLD}[6]{RESET} 📋 {BOLD}View Client Connection Snippets{RESET}")
        print(f"  {BOLD}[7]{RESET} ⚙️ {BOLD}Edit Configuration{RESET}")
        print(f"  {BOLD}[0]{RESET} 🛑 {DIM}Exit{RESET}")
        print()

        try:
            choice = input(f"{BOLD}Select an option [0-7]:{RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{DIM}Goodbye!{RESET}")
            break

        if choice == "1":
            class DummyArgs:
                open = True
                port = CONFIG.get("port", 8081)
            cmd_start(DummyArgs())
            break
        elif choice == "2":
            cmd_login()
        elif choice == "3":
            cmd_chat()
        elif choice == "4":
            cmd_status()
            input(f"{DIM}Press Enter to return to menu...{RESET}")
        elif choice == "5":
            cmd_logout()
            input(f"{DIM}Press Enter to return to menu...{RESET}")
        elif choice == "6":
            cmd_client()
            input(f"{DIM}Press Enter to return to menu...{RESET}")
        elif choice == "7":
            print(f"\n{BOLD}Current Config:{RESET}")
            print(json.dumps(CONFIG, indent=2))
            input(f"{DIM}Press Enter to return to menu...{RESET}")
        elif choice in ("0", "q", "exit"):
            print(f"\n{DIM}Goodbye!{RESET}")
            break
        else:
            print(f"{YELLOW}Invalid choice, please select 0-7{RESET}")
            time.sleep(1)


def main():
    config_path = os.environ.get("GEMINI_WEB2API_CONFIG") or find_config()
    if config_path:
        load_config(config_path)

    parser = argparse.ArgumentParser(
        prog="gemini-web2api",
        description="Gemini Web to OpenAI API - Interactive CLI & Proxy Server"
    )
    parser.add_argument("--version", action="version", version=f"gemini-web2api {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # start subcommand
    p_start = subparsers.add_parser("start", help="Start the proxy server")
    p_start.add_argument("--port", "-p", type=int, default=None, help="Port to listen on (default 8081)")
    p_start.add_argument("--open", "-o", action="store_true", help="Automatically open web dashboard in browser")

    # login subcommand
    p_login = subparsers.add_parser("login", help="Launch automated browser login to capture cookies")
    p_login.add_argument("--browser", type=str, default=None, help="Path to browser executable")
    p_login.add_argument("--profile-dir", type=str, default=None, help="Browser profile directory")
    p_login.add_argument("--headless", action="store_true", help="Run in headless mode")

    # logout subcommand
    subparsers.add_parser("logout", help="Log out and reset to anonymous mode")

    # dash subcommand
    p_dash = subparsers.add_parser("dash", help="Start server and automatically open /dash in browser")
    p_dash.add_argument("--port", "-p", type=int, default=None, help="Port to listen on (default 8081)")

    # chat subcommand
    p_chat = subparsers.add_parser("chat", help="Start interactive terminal chat session")
    p_chat.add_argument("--model", "-m", type=str, default="gemini-3.5-flash-thinking", help="Model to use")

    # status subcommand
    subparsers.add_parser("status", help="Display auth validity and server health")

    # client subcommand
    subparsers.add_parser("client", help="Display client integration snippets")

    # config subcommand
    p_cfg = subparsers.add_parser("config", help="View or update configuration")
    p_cfg.add_argument("--port", type=int, default=None, help="Update server port")
    p_cfg.add_argument("--proxy", type=str, default=None, help="Update proxy URL")
    p_cfg.add_argument("--model", type=str, default=None, help="Update default model")

    # menu subcommand
    subparsers.add_parser("menu", help="Launch interactive TUI menu")

    # Allow legacy top-level flags
    parser.add_argument("--port", type=int, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--config", type=str, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--cookie-file", type=str, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--proxy", type=str, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--login", action="store_true", help=argparse.SUPPRESS)

    args = parser.parse_args()

    # Dispatch subcommands
    if args.command == "dash":
        setattr(args, "open", True)
        cmd_start(args)
    elif args.command == "start":
        cmd_start(args)
    elif args.command == "login":
        cmd_login(args)
    elif args.command == "logout":
        cmd_logout(args)
    elif args.command == "chat":
        cmd_chat(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "client":
        cmd_client(args)
    elif args.command == "config":
        cmd_config(args)
    elif args.command == "menu":
        interactive_menu()
    elif len(sys.argv) == 1:
        # Default action: start server and automatically open /dash in browser!
        class DefaultArgs:
            open = True
            port = CONFIG.get("port", 8081)
        cmd_start(DefaultArgs())
    else:
        # Legacy flag fallback
        if getattr(args, "login", False):
            cmd_login(args)
        if getattr(args, "port", None):
            CONFIG["port"] = args.port
        if getattr(args, "cookie_file", None):
            CONFIG["cookie_file"] = args.cookie_file
        if getattr(args, "proxy", None):
            CONFIG["proxy"] = args.proxy
        cmd_start(args)



if __name__ == "__main__":
    main()
