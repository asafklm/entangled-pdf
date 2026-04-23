#!/bin/bash
set -e

INSTALL_DIR="${HOME}/.local/share/entangledpdf"
FRONTEND_BUILT="false"
SKIP_CERTS=false
USE_EDITABLE=false

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Installs EntangledPdf with a local Python virtual environment at ./bin/"
    echo "This ensures consistent dependencies across development and CI environments."
    echo
    echo "Options:"
    echo "  --ci              CI mode: skip SSL certs, use editable install"
    echo "  --editable        Install package in editable mode (pip install -e .)"
    echo "  --skip-certs      Skip SSL certificate generation"
    echo "  -h, --help        Show this help message"
    echo
    echo "Environment variables:"
    echo "  ENTANGLEDPDF_API_KEY    API key for the server"
    echo
    echo "After installation, use ./bin/entangle-pdf to run commands:"
    echo "  ./bin/entangle-pdf start"
    echo "  ./bin/entangle-pdf sync <pdf> <line>:<column>:<texfile>"
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

# Create local virtual environment for consistent development and testing
echo "Setting up Python virtual environment..."
VENV_DIR="${REPO_DIR}/bin"
if [ ! -f "${VENV_DIR}/python" ]; then
    echo "Creating virtual environment at ${VENV_DIR}..."
    python3 -m venv "$VENV_DIR"
    echo "Virtual environment created."
    echo "Contents of ${VENV_DIR}:"
    ls -la "$VENV_DIR" || echo "Directory does not exist"
else
    echo "Virtual environment already exists at ${VENV_DIR}."
fi
echo

echo "Installing Python dependencies into virtual environment..."
if [ "$USE_EDITABLE" = "true" ]; then
    echo "Installing in editable mode..."
    "${VENV_DIR}/python" -m pip install -e .
else
    echo "Installing in standard mode..."
    "${VENV_DIR}/python" -m pip install .
fi
echo "Python dependencies installed into ${VENV_DIR}."
echo

echo "Building frontend..."
npm install
npm run build
FRONTEND_BUILT="true"
echo "Frontend built."
echo

if [ "$SKIP_CERTS" = "false" ]; then
    echo "Generating SSL certificates..."
    "${VENV_DIR}/python" -m entangledpdf.certs generate || true
    echo "SSL certificates generated."
    echo
fi

echo "=== Installation Complete ==="
echo
echo "A Python virtual environment has been created at: ${VENV_DIR}"
echo
echo "Next steps:"
echo "  1. Add API key to your shell:"
echo "     ./bin/entangle-pdf generate-api-key --shell >> ~/.bashrc"
echo "     source ~/.bashrc"
echo
echo "  2. Start the server:"
echo "     ./bin/entangle-pdf start"
echo
echo "  3. Open browser and accept SSL certificate:"
echo "     - Open https://localhost:8431/view in your browser"
echo "     - Click 'Advanced' → 'Accept' to proceed (self-signed cert)"
echo "     - Enter the token shown in the terminal"
echo
echo "  4. Test loading a PDF with forward search:"
echo "     ./bin/entangle-pdf sync examples/example.pdf 10:1:example.tex"
echo "     # Format: ./bin/entangle-pdf sync <pdf> <line>:<column>:<texfile>"
echo
echo "  5. Configure forward search in your editor:"
echo "     - The sync command works with any editor: ./bin/entangle-pdf sync <pdf> <line>:<col>:<tex>"
echo "     - See README.md for VimTeX/neovim setup examples"
echo
echo "  6. For inverse search (PDF → editor, optional):"
echo "     # Example for Neovim:"
echo "     ./bin/entangle-pdf start --inverse-search-nvim"
echo "     # Or use custom command:"
echo "     ./bin/entangle-pdf start --inverse-search-command 'nvr --remote-silent +%{line} %{file}'"
echo "     - See README.md for editor-specific setup (neovim/emacs/vim)"
echo
echo "For full setup instructions, see: ${REPO_DIR}/README.md"
