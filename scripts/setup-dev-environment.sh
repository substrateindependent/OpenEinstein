#!/bin/bash
# OpenEinstein — Developer Environment Setup Script (macOS)
# Run this on your Mac to install all dependencies for full integration testing.
#
# Usage:
#   chmod +x scripts/setup-dev-environment.sh
#   ./scripts/setup-dev-environment.sh
#
# This script is idempotent — safe to run multiple times.

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; }
check() { command -v "$1" &>/dev/null; }

echo "============================================"
echo " OpenEinstein Dev Environment Setup (macOS)"
echo "============================================"
echo ""

# --- Homebrew ---
if ! check brew; then
    warn "Homebrew not found. Installing..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    info "Homebrew already installed"
fi

# --- Python 3.12+ ---
if check python3 && python3 -c "import sys; exit(0 if sys.version_info >= (3, 12) else 1)" 2>/dev/null; then
    info "Python $(python3 --version | cut -d' ' -f2) already installed"
else
    warn "Installing Python 3.12..."
    brew install python@3.12
fi

# --- Node.js (for arXiv MCP server via npx) ---
if check node; then
    info "Node.js $(node --version) already installed"
else
    warn "Installing Node.js..."
    brew install node
fi

if check npx; then
    info "npx available"
else
    error "npx not found even after Node install — check your PATH"
fi

# --- Docker ---
if check docker; then
    info "Docker already installed"
    if docker info &>/dev/null; then
        info "Docker daemon is running"
    else
        warn "Docker is installed but daemon is not running. Start Docker Desktop."
    fi
else
    warn "Installing Docker..."
    brew install --cask docker
    warn "Docker Desktop installed — you'll need to open it once to complete setup."
fi

# --- LaTeX (BasicTeX + latexmk) ---
if check latexmk; then
    info "latexmk already installed"
else
    warn "Installing BasicTeX + latexmk..."
    brew install --cask basictex
    # BasicTeX needs PATH update
    eval "$(/usr/libexec/path_helper)"
    export PATH="/Library/TeX/texbin:$PATH"
    # Install latexmk via tlmgr
    sudo tlmgr update --self
    sudo tlmgr install latexmk
    info "latexmk installed"
fi

# --- Git ---
if check git; then
    info "Git $(git --version | cut -d' ' -f3) already installed"
else
    brew install git
fi

# --- Wolfram Engine (free developer license) ---
if check wolframscript; then
    info "Wolfram Engine already installed"
    # Check if activated
    if wolframscript -code '1+1' 2>/dev/null | grep -q "2"; then
        info "Wolfram Engine is activated and working"
    else
        warn "Wolfram Engine installed but may not be activated."
        warn "Run: wolframscript -activate"
    fi
else
    echo ""
    warn "Wolfram Engine is NOT installed."
    echo "  To install (free for developers):"
    echo "  1. Go to: https://www.wolfram.com/engine/"
    echo "  2. Create a Wolfram ID (free)"
    echo "  3. Download Wolfram Engine for Mac"
    echo "  4. Install the .dmg"
    echo "  5. Activate: wolframscript -activate"
    echo ""
    echo "  For xAct (tensor algebra package):"
    echo "  git clone https://github.com/xAct-contrib/xAct ~/Library/Mathematica/Applications/xAct"
    echo ""
fi

# --- Python project setup ---
echo ""
echo "--- Python Project Setup ---"
cd "$(dirname "$0")/.."

if [ -f "pyproject.toml" ]; then
    info "Found pyproject.toml"
    if [ ! -d ".venv" ]; then
        warn "Creating local virtual environment at .venv..."
        python3 -m venv .venv
    fi
    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/pip install -e ".[dev]"
    info "OpenEinstein installed in development mode (.venv)"
else
    error "pyproject.toml not found. Run this script from the repo root."
fi

# --- .env file ---
if [ -f ".env" ]; then
    info ".env file exists"
else
    warn "Creating .env from .env.example..."
    cp .env.example .env
    warn "Edit .env to fill in your API keys!"
fi

# --- Summary ---
echo ""
echo "============================================"
echo " Environment Check Summary"
echo "============================================"
echo ""
check python3    && info "Python:        $(python3 --version 2>&1)" || error "Python:        NOT FOUND"
check node       && info "Node.js:       $(node --version 2>&1)"    || error "Node.js:       NOT FOUND"
check npx        && info "npx:           available"                  || error "npx:           NOT FOUND"
check docker     && info "Docker:        installed"                  || error "Docker:        NOT FOUND"
check latexmk    && info "latexmk:       installed"                  || error "latexmk:       NOT FOUND"
check wolframscript && info "Wolfram:    installed"                  || warn  "Wolfram:       NOT INSTALLED (optional)"
check git        && info "Git:           $(git --version 2>&1 | cut -d' ' -f3)" || error "Git: NOT FOUND"

echo ""
echo "--- API Keys Status (from .env) ---"
if [ -f ".env" ]; then
    source .env 2>/dev/null
    [ -n "$ANTHROPIC_API_KEY" ]  && info "ANTHROPIC_API_KEY:  set" || warn "ANTHROPIC_API_KEY:  not set"
    [ -n "$OPENAI_API_KEY" ]     && info "OPENAI_API_KEY:     set" || warn "OPENAI_API_KEY:     not set"
    [ -n "$GOOGLE_API_KEY" ]     && info "GOOGLE_API_KEY:     set" || warn "GOOGLE_API_KEY:     not set"
    [ -n "$S2_API_KEY" ]         && info "S2_API_KEY:         set" || warn "S2_API_KEY:         not set"
    [ -n "$ADS_API_KEY" ]        && info "ADS_API_KEY:        set" || warn "ADS_API_KEY:        not set"
    [ -n "$ZOTERO_API_KEY" ]     && info "ZOTERO_API_KEY:     set" || warn "ZOTERO_API_KEY:     not set"
fi

echo ""
echo "Next steps:"
echo "  1. Fill in API keys in .env (see below for links)"
echo "  2. Install Wolfram Engine if you want Mathematica tests"
echo "  3. Run: pytest  (to verify everything works)"
echo ""
echo "API key signup links:"
echo "  Semantic Scholar: https://www.semanticscholar.org/product/api#api-key-form"
echo "  NASA ADS:         https://ui.adsabs.harvard.edu/user/settings/token"
echo "  Zotero:           https://www.zotero.org/settings/keys"
echo "  Wolfram:          https://www.wolfram.com/engine/"
echo ""
