#!/usr/bin/env bash
set -e

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}=== Installing gemini-web2api ===${NC}"

# Check for uv, install if missing
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}[*] uv not found. Installing uv...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

if command -v uv &> /dev/null; then
    echo -e "${CYAN}[*] Installing gemini-web2api globally via uv...${NC}"
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    uv tool install "${SCRIPT_DIR}" --force
elif command -v pipx &> /dev/null; then
    echo -e "${CYAN}[*] Installing gemini-web2api globally via pipx...${NC}"
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    pipx install "${SCRIPT_DIR}" --force
else
    echo -e "${CYAN}[*] Installing gemini-web2api via pip...${NC}"
    pip install -e .
fi

echo -e "\n${GREEN}✓ gemini-web2api installed successfully!${NC}"
echo -e "Try running:"
echo -e "  ${CYAN}gemini-web2api login${NC}  # Sign in to Google / Gemini"
echo -e "  ${CYAN}gemini-web2api${NC}        # Start proxy server & open dashboard"
echo -e "  ${CYAN}gemini-web2api chat${NC}   # Terminal chat REPL"
