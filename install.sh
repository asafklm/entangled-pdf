#!/bin/bash
set -e

INSTALL_DIR="${HOME}/.local/share/entangledpdf"
FRONTEND_BUILT="false"
SKIP_CERTS=false
USE_EDITABLE=false

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --ci              CI mode: use pip, skip SSL certs, editable install"
    echo "  --editable        Install package in editable mode (pip install -e .)"
    echo "  --skip-certs      Skip SSL certificate generation"
    echo "  -h, --help        Show this help message"
    echo
    echo "Environment variables:"
    echo "  ENTANGLEDPDF_API_KEY    API key for the server"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --ci)
            SKIP_CERTS=true
            USE_EDITABLE=true
            shift
            ;;
        --editable)
            USE_EDITABLE=true
            shift
            ;;
        --skip-certs)
            SKIP_CERTS=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

echo "=== EntangledPdf Installation ==="
echo

check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "Error: '$1' is required but not installed."
        exit 1
    fi
}

echo "Checking prerequisites..."
check_command git
check_command pip3 || check_command pip
check_command npm
echo "Prerequisites OK."
echo

if [ -d ".git" ]; then
    echo "Installing from local repository..."
    REPO_DIR="$(pwd)"
else
    echo "Cloning repository..."
    check_command git
    REPO_DIR="${INSTALL_DIR}/src"
    mkdir -p "$(dirname "${REPO_DIR}")"
    git clone https://github.com/asafklm/entangled-pdf.git "${REPO_DIR}"
    cd "${REPO_DIR}"
fi
echo "Working in: ${REPO_DIR}"
echo

echo "Installing Python dependencies..."
if command -v pipx &> /dev/null && [ "$USE_EDITABLE" = "false" ]; then
    echo "Using pipx..."
    pipx install .
elif command -v pip3 &> /dev/null; then
    echo "Using pip3..."
    if [ "$USE_EDITABLE" = "true" ]; then
        pip3 install -e .
    else
        pip3 install .
    fi
elif command -v pip &> /dev/null; then
    echo "Using pip..."
    if [ "$USE_EDITABLE" = "true" ]; then
        pip install -e .
    else
        pip install .
    fi
else
    echo "Error: No pip or pipx found."
    exit 1
fi
echo "Python dependencies installed."
echo

echo "Building frontend..."
npm install
npm run build
FRONTEND_BUILT="true"
echo "Frontend built."
echo

if [ "$SKIP_CERTS" = "false" ]; then
    echo "Generating SSL certificates..."
    python3 -m entangledpdf.certs generate || true
    echo "SSL certificates generated."
    echo
fi

echo "=== Installation Complete ==="
echo
echo "Next steps:"
echo "  1. Add API key to your shell:"
echo "     entangle-pdf generate-api-key --shell >> ~/.bashrc"
echo "     source ~/.bashrc"
echo
echo "  2. Start the server:"
echo "     entangle-pdf start"
echo
echo "  3. Open browser and accept SSL certificate:"
echo "     - Open https://localhost:8431/view in your browser"
echo "     - Click 'Advanced' → 'Accept' to proceed (self-signed cert)"
echo "     - Enter the token shown in the terminal"
echo
echo "  4. Test loading a PDF with forward search:"
echo "     entangle-pdf sync examples/example.pdf 10:1:example.tex"
echo "     # Format: entangle-pdf sync <pdf> <line>:<column>:<texfile>"
echo
echo "  5. Configure forward search in your editor:"
echo "     - The sync command works with any editor: entangle-pdf sync <pdf> <line>:<col>:<tex>"
echo "     - See README.md for VimTeX/neovim setup examples"
echo
echo "  6. For inverse search (PDF → editor, optional):"
echo "     # Example for Neovim:"
echo "     entangle-pdf start --inverse-search-nvim"
echo "     # Or use custom command:"
echo "     entangle-pdf start --inverse-search-command 'nvr --remote-silent +%{line} %{file}'"
echo "     - See README.md for editor-specific setup (neovim/emacs/vim)"
echo
echo "For full setup instructions, see: ${REPO_DIR}/README.md"
