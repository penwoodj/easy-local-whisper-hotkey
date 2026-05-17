#!/usr/bin/env bash
set -euo pipefail

# Setup script for easy-local-whisper-hotkey
# This script bootstraps the project after cloning

# Detect repository root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== First-time setup for easy-local-whisper-hotkey ==="
echo "Repository root: $REPO_ROOT"
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found"
    echo "Please install Python 3.11 or later"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
INSTALLED_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
INSTALLED_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$INSTALLED_MAJOR" -lt 3 ] || ([ "$INSTALLED_MAJOR" -eq 3 ] && [ "$INSTALLED_MINOR" -lt 11 ]); then
    echo "ERROR: python3 >= 3.11 required (found $PYTHON_VERSION)"
    exit 1
fi

echo "  ✓ python3 $PYTHON_VERSION"

if ! command -v docker &>/dev/null; then
    echo "ERROR: docker not found"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi
echo "  ✓ docker"

if ! docker compose version &>/dev/null; then
    echo "ERROR: docker compose not found"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi
echo "  ✓ docker compose"

if ! command -v xdotool &>/dev/null; then
    echo "WARNING: xdotool not found (required for dictation)"
    echo "Install with: sudo apt-get install xdotool"
fi
echo "  ✓ xdotool"

echo ""

# Create Python venv
VENV="$REPO_ROOT/.venv"
echo "Creating virtual environment at $VENV..."
if [ ! -d "$VENV" ]; then
    python3 -m venv "$VENV"
    echo "  ✓ venv created"
else
    echo "  ✓ venv already exists"
fi

# Activate venv
# shellcheck source=/dev/null
source "$VENV/bin/activate"

# Upgrade pip
echo ""
echo "Upgrading pip..."
python3 -m pip install --upgrade pip
echo "  ✓ pip upgraded"

# Install package with dev dependencies
echo ""
echo "Installing package with dev dependencies..."
pip install -e ".[dev]"
echo "  ✓ package installed"

# Set up .env file
echo ""
echo "Setting up .env file..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "  ✓ .env created from .env.example"
else
    echo "  ✓ .env already exists"
fi

# Create socket directory
SOCKET_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/whisper"
echo ""
echo "Creating socket directory at $SOCKET_DIR..."
mkdir -p "$SOCKET_DIR" || {
    echo "ERROR: Failed to create $SOCKET_DIR"
    exit 1
}
chmod 700 "$SOCKET_DIR"
echo "  ✓ socket directory created"

# Build and start Docker container
echo ""
echo "Building and starting Docker container..."
docker compose up -d --build
echo "  ✓ Docker container started"

# Wait for socket
WAIT_TIMEOUT=30
echo ""
echo "Waiting for inference server socket (timeout: ${WAIT_TIMEOUT}s)..."
elapsed=0
while [ $elapsed -lt $WAIT_TIMEOUT ]; do
    if [ -S "$SOCKET_DIR/whisper.sock" ]; then
        echo "  ✓ socket found"
        break
    fi
    sleep 1
    elapsed=$((elapsed + 1))
done

if [ $elapsed -eq $WAIT_TIMEOUT ]; then
    echo "  ✗ socket not found after ${WAIT_TIMEOUT} seconds"
    echo ""
    echo "Running diagnostics..."
    python3 -m whisper_hotkey.cli doctor || true
    echo ""
    echo "Setup completed with warnings. Check the output above."
    exit 1
fi

# Run diagnostics
echo ""
echo "Running diagnostics..."
python3 -m whisper_hotkey.cli doctor

# Success
echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Run: easy-local-whisper-hotkey run"
echo "  2. Press Ctrl+Space to record"
echo ""
echo "For more information, see: docs/install.md"