#!/bin/bash
# ============================================================================
# Claudia Chatterley — Full Installer for macOS
#
# Handles everything from a completely fresh Mac:
#   1. Installs Homebrew (if missing)
#   2. Installs Python 3.12 (if Python < 3.10)
#   3. Installs portaudio (for microphone access)
#   4. Installs Claudia Chatterley
#
# Usage (from the Internet):
#   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/sevsorensen/claudia-chatterley/main/setup.sh)"
#
# Usage (local, after cloning the repo):
#   chmod +x setup.sh && ./setup.sh
# ============================================================================

set -e

BOLD="\033[1m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
BLUE="\033[34m"
RESET="\033[0m"

echo ""
echo -e "${BOLD}🎤 Claudia Chatterley Installer${RESET}"
echo "   Voice-to-text for Claude Cowork & macOS"
echo ""

# ────────────────────────────────────────────
# Step 0: Check that we're on macOS
# ────────────────────────────────────────────
if [[ "$(uname)" != "Darwin" ]]; then
    echo -e "${RED}Error: Claudia Chatterley requires macOS.${RESET}"
    exit 1
fi
echo -e "  ✓ macOS detected"

# ────────────────────────────────────────────
# Step 1: Homebrew
# ────────────────────────────────────────────
if ! command -v brew &> /dev/null; then
    echo ""
    echo -e "${YELLOW}Homebrew is not installed.${RESET}"
    echo "  Homebrew is a free package manager for macOS."
    echo "  Claudia needs it to install audio libraries and Python."
    echo ""
    read -p "  Install Homebrew now? (y/n) " -n 1 -r < /dev/tty
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "${BLUE}Installing Homebrew (this may take a few minutes)...${RESET}"
        echo "  You may be asked for your Mac password. That is normal."
        echo ""
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

        # Add Homebrew to PATH for this session (Apple Silicon vs Intel)
        if [[ -f "/opt/homebrew/bin/brew" ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        elif [[ -f "/usr/local/bin/brew" ]]; then
            eval "$(/usr/local/bin/brew shellenv)"
        fi

        # Verify it worked
        if ! command -v brew &> /dev/null; then
            echo ""
            echo -e "${RED}Homebrew installed but not in PATH yet.${RESET}"
            echo "  Close this Terminal window, open a new one, and run this script again."
            exit 1
        fi

        echo -e "  ✓ Homebrew installed"
    else
        echo ""
        echo -e "${RED}Cannot continue without Homebrew.${RESET}"
        echo "  You can install it manually at https://brew.sh"
        exit 1
    fi
else
    echo -e "  ✓ Homebrew found"
fi

# ────────────────────────────────────────────
# Step 2: Python 3.10+
# ────────────────────────────────────────────
NEED_PYTHON=false

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [[ $PYTHON_MAJOR -lt 3 ]] || [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 10 ]]; then
        echo ""
        echo -e "${YELLOW}Python $PYTHON_VERSION found — Claudia needs 3.10 or newer.${RESET}"
        echo "  (Your current Python came with macOS. It will not be changed.)"
        NEED_PYTHON=true
    else
        echo -e "  ✓ Python $PYTHON_VERSION detected"
    fi
else
    echo -e "${YELLOW}Python 3 not found.${RESET}"
    NEED_PYTHON=true
fi

if [[ "$NEED_PYTHON" == true ]]; then
    echo ""
    read -p "  Install Python 3.12 via Homebrew? (y/n) " -n 1 -r < /dev/tty
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Installing Python 3.12...${RESET}"
        brew install python@3.12
        echo -e "  ✓ Python 3.12 installed"

        # Use the Homebrew Python from now on
        if command -v python3.12 &> /dev/null; then
            PYTHON_CMD="python3.12"
            PIP_CMD="pip3.12"
        elif [[ -f "$(brew --prefix)/bin/python3.12" ]]; then
            PYTHON_CMD="$(brew --prefix)/bin/python3.12"
            PIP_CMD="$(brew --prefix)/bin/pip3.12"
        else
            PYTHON_CMD="python3"
            PIP_CMD="pip3"
        fi
    else
        echo ""
        echo -e "${RED}Cannot continue without Python 3.10+.${RESET}"
        echo "  Install manually: brew install python@3.12"
        exit 1
    fi
else
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
fi

# Confirm Python version
FINAL_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "  ✓ Using Python $FINAL_VERSION ($PYTHON_CMD)"

# ────────────────────────────────────────────
# Step 3: portaudio (required for microphone)
# ────────────────────────────────────────────
if ! brew list portaudio &> /dev/null 2>&1; then
    echo ""
    echo -e "${BLUE}Installing portaudio (required for microphone access)...${RESET}"
    brew install portaudio
    echo -e "  ✓ portaudio installed"
else
    echo -e "  ✓ portaudio found"
fi

# ────────────────────────────────────────────
# Step 3b: pipx (for safe CLI app installation)
# ────────────────────────────────────────────
PIPX_CMD=""
if command -v pipx &> /dev/null; then
    PIPX_CMD="pipx"
    echo -e "  ✓ pipx found"
elif [[ -f "$(brew --prefix)/bin/pipx" ]]; then
    PIPX_CMD="$(brew --prefix)/bin/pipx"
    echo -e "  ✓ pipx found"
else
    echo ""
    echo -e "${BLUE}Installing pipx (manages Python CLI tools safely)...${RESET}"
    brew install pipx
    # Use full path since PATH may not be updated in this session
    PIPX_CMD="$(brew --prefix)/bin/pipx"
    $PIPX_CMD ensurepath 2>/dev/null || true
    echo -e "  ✓ pipx installed"
fi

# ────────────────────────────────────────────
# Step 4: Install Claudia Chatterley
# ────────────────────────────────────────────
echo ""
echo -e "${BOLD}Installing Claudia Chatterley...${RESET}"

GITHUB_REPO="git+https://github.com/sevsorensen/claudia-chatterley.git"

if [[ -d "claudia" ]] && [[ -f "pyproject.toml" ]]; then
    # Local install (running from inside the cloned repo)
    $PIPX_CMD install -e . --python $PYTHON_CMD || $PIP_CMD install -e . --user --break-system-packages
else
    # Install from GitHub
    $PIPX_CMD install "$GITHUB_REPO" --python $PYTHON_CMD || $PIP_CMD install "$GITHUB_REPO" --user --break-system-packages
fi

# ────────────────────────────────────────────
# Step 5: Verify installation
# ────────────────────────────────────────────
echo ""
if command -v claudia &> /dev/null; then
    CLAUDIA_VERSION=$(claudia --version 2>/dev/null || echo "installed")
    echo -e "${GREEN}${BOLD}✓ Claudia Chatterley $CLAUDIA_VERSION${RESET}"
else
    # May need to use full path
    CLAUDIA_PATH="$($PYTHON_CMD -c 'import site; print(site.USER_BASE)')/bin/claudia"
    if [[ -f "$CLAUDIA_PATH" ]]; then
        echo -e "${GREEN}${BOLD}✓ Claudia Chatterley installed${RESET}"
        echo ""
        echo -e "  ${YELLOW}Note: Add this to your PATH to run 'claudia' from anywhere:${RESET}"
        echo "  export PATH=\"\$($PYTHON_CMD -c 'import site; print(site.USER_BASE)')/bin:\$PATH\""
        echo ""
        echo "  Or run directly:"
        echo "  $PYTHON_CMD -m claudia"
    else
        echo -e "${GREEN}${BOLD}✓ Claudia Chatterley installed${RESET}"
    fi
fi

echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}  What to do next:${RESET}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo "  1. ${BOLD}Grant Accessibility permission${RESET} (required for auto-paste):"
echo ""
echo "     System Settings > Privacy & Security > Accessibility"
echo "     Click the + button and add Terminal"
echo ""
echo "  2. ${BOLD}Launch Claudia:${RESET}"
echo ""
echo "     claudia"
echo "     (or: $PYTHON_CMD -m claudia)"
echo ""
echo "  3. macOS will ask for ${BOLD}Microphone permission${RESET} on first use."
echo "     Click Allow."
echo ""
echo "  4. Click the floating 🎤 button and start speaking!"
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo "  Optional — Use Groq for cloud transcription (faster):"
echo "     export CLAUDIA_GROQ_API_KEY=your-key-here"
echo "     claudia --engine groq"
echo ""
echo "  All options:"
echo "     claudia --help"
echo ""
