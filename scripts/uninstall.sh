#!/usr/bin/env bash
set -euo pipefail

if systemctl --user --quiet is-enabled whisper-hotkey.service 2>/dev/null; then
  systemctl --user disable --now whisper-hotkey.service || true
fi

rm -f "$HOME/.config/systemd/user/whisper-hotkey.service"
systemctl --user daemon-reload || true

if command -v pipx >/dev/null 2>&1; then
  pipx uninstall easy-local-whisper-hotkey || true
else
  python3 -m pip uninstall -y easy-local-whisper-hotkey || true
fi

echo "Removed whisper-hotkey package and user service."
