#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

SERVICE_SOURCE="$PROJECT_ROOT/packaging/systemd/whisper-hotkey.service"
SERVICE_DEST="$HOME/.config/systemd/user/whisper-hotkey.service"

mkdir -p "$HOME/.config/systemd/user"
cp "$SERVICE_SOURCE" "$SERVICE_DEST"

systemctl --user daemon-reload
echo "Service installed to $SERVICE_DEST"
echo "Enable with: systemctl --user enable --now whisper-hotkey.service"
