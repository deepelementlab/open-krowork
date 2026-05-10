#!/usr/bin/env bash
# Open-KroWork One-Click Installer
# Usage: bash install.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  Open-KroWork Installer${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# Step 1: Check Python
echo -e "${YELLOW}[1/4] Checking Python...${NC}"
if command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python &>/dev/null; then
    PYTHON="python"
else
    echo -e "${RED}Error: Python 3.9+ not found. Please install Python first.${NC}"
    exit 1
fi

PY_VERSION=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "  Python version: ${GREEN}$PY_VERSION${NC}"

if $PYTHON -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)"; then
    echo -e "  ${GREEN}OK${NC}"
else
    echo -e "${RED}Error: Python 3.9+ required, found $PY_VERSION${NC}"
    exit 1
fi

# Step 2: Install dependencies
echo ""
echo -e "${YELLOW}[2/4] Installing Python dependencies...${NC}"
$PYTHON -m pip install -r "$SCRIPT_DIR/requirements.txt" --quiet
echo -e "  ${GREEN}OK${NC}"

# Step 3: Verify installation
echo ""
echo -e "${YELLOW}[3/4] Verifying installation...${NC}"
$PYTHON -c "
import requests, bs4, PIL
print('  All dependencies verified')
" || {
    echo -e "${RED}Dependency verification failed. Try: pip install -r requirements.txt${NC}"
    exit 1
}

# Step 4: Create directory structure
echo ""
echo -e "${YELLOW}[4/4] Setting up directories...${NC}"
mkdir -p "$HOME/.krowork/apps"
echo -e "  Created ~/.krowork/apps/"
echo -e "  ${GREEN}OK${NC}"

# Done
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Installation complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "Next steps:"
echo ""
echo -e "  Mode 1 (Plugin):"
echo -e "    ${CYAN}claude --plugin-dir $SCRIPT_DIR${NC}"
echo ""
echo -e "  Mode 2 (Global MCP):"
echo -e "    ${CYAN}claude mcp add krowork -s user -- python $SCRIPT_DIR/server/main.py${NC}"
echo -e "    ${CYAN}claude${NC}"
echo ""
echo -e "  Then create your first app:"
echo -e "    ${CYAN}> /krowork:create \"My first app - describe what it does\"${NC}"
