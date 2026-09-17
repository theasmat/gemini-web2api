"""Interactive Terminal REPL Chat for Gemini Web2API."""
import sys
import os
import time
import readline
import argparse

from .config import CONFIG, load_config, find_config
from .models import MODELS, resolve_model
from .gemini import generate_stream, get_auth_details


# ANSI colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_banner(model_name: str, think_mode: int):
    auth = get_auth_details()
    auth_str = f"{GREEN}Authenticated (Pro Ready){RESET}" if auth.get("pro_ready") else (
        f"{GREEN}Authenticated{RESET}" if auth.get("authenticated") else f"{CYAN}Anonymous Mode{RESET}"
    )
    print()
    print(f"{BOLD}{MAGENTA}✦ Gemini Web2API Interactive Chat ✦{RESET}")
    print(f"  {DIM}Model:{RESET}   {CYAN}{model_name}{RESET} (think depth: {think_mode})")
    print(f"  {DIM}Auth:{RESET}    {auth_str}")
    print(f"  {DIM}Commands:{RESET} {DIM}/model <name>, /think <0-4>, /clear, /status, /exit{RESET}")
    print(f"{DIM}{'─' * 60}{RESET}")
    print()


def run_chat_repl(initial_model: str = "gemini-3.5-flash-thinking"):
    """Run interactive terminal chat loop."""
    config_path = find_config()
    if config_path:
        load_config(config_path)

    current_model_str = initial_model
    history = []

    print_banner(current_model_str, 0)

    while True:
        try:
            print(f"{BOLD}{GREEN}You:{RESET} ", end="", flush=True)
            user_input = input().strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{DIM}Goodbye!{RESET}")
            break

        if not user_input:
            continue

        # Commands
        if user_input in ("/exit", "/quit", "exit", "quit"):
            print(f"{DIM}Goodbye!{RESET}")
            break

        if user_input == "/clear":
            history.clear()
            os.system("clear" if os.name == "posix" else "cls")
            print_banner(current_model_str, 0)
            print(f"{DIM}[Conversation cleared]{RESET}\n")
            continue

        if user_input == "/status":
            auth = get_auth_details()
            print(f"\n{BOLD}Authentication Details:{RESET}")
            for k, v in auth.items():
                print(f"  {DIM}{k}:{RESET} {v}")
            print()
            continue

        if user_input.startswith("/model"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                current_model_str = parts[1].strip()
                print(f"{CYAN}Switched model to: {current_model_str}{RESET}\n")
            else:
                print(f"{CYAN}Available models: {', '.join(MODELS.keys())}{RESET}\n")
            continue

        if user_input.startswith("/think"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                depth = parts[1].strip()
                current_model_str = current_model_str.split("@think=")[0] + f"@think={depth}"
                print(f"{CYAN}Thinking depth set: {current_model_str}{RESET}\n")
            else:
                print(f"{CYAN}Specify depth 0 (deepest) to 4 (shallowest), e.g. /think 0{RESET}\n")
            continue

        # Prepare messages
        history.append({"role": "user", "content": user_input})
        from .tools import messages_to_prompt
        prompt, images = messages_to_prompt(history)

        model_name, model_id, think_mode, err, extra_fields = resolve_model(current_model_str)
        if err:
            print(f"{YELLOW}[Error resolving model: {err}]{RESET}\n")
            continue

        print(f"\n{BOLD}{CYAN}Gemini:{RESET} ", end="", flush=True)
        full_response = ""
        try:
            for chunk in generate_stream(prompt, model_id, think_mode, extra_fields=extra_fields):
                print(chunk, end="", flush=True)
                full_response += chunk
            print("\n")
            history.append({"role": "assistant", "content": full_response})
        except Exception as e:
            print(f"\n{YELLOW}[Error: {e}]{RESET}\n")


def main():
    parser = argparse.ArgumentParser(description="Interactive Gemini Terminal Chat")
    parser.add_argument("--model", "-m", type=str, default="gemini-3.5-flash-thinking", help="Model name")
    args = parser.parse_args()
    run_chat_repl(args.model)


if __name__ == "__main__":
    main()
