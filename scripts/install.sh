#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENABLE_SERVICE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --enable-service)
      ENABLE_SERVICE=1
      shift
      ;;
    *)
      shift
      ;;
  esac
done

WHEEL_PATH="$(find "$ROOT_DIR/dist" -maxdepth 1 -name 'easy_local_whisper_hotkey-*.whl' 2>/dev/null | sort | tail -n 1 || true)"

if [[ -n "$WHEEL_PATH" && -f "$WHEEL_PATH" ]]; then
  if command -v pipx >/dev/null 2>&1; then
    pipx install --force "$WHEEL_PATH"
  else
    python3 -m pip install --user --force-reinstall "$WHEEL_PATH"
  fi
else
  python3 -m pip install --user -e "$ROOT_DIR"
fi

mkdir -p "$HOME/.config/systemd/user"
mkdir -p "$HOME/.config/whisper-hotkey"

cp "$ROOT_DIR/packaging/systemd/whisper-hotkey.service" "$HOME/.config/systemd/user/whisper-hotkey.service"

ENV_FILE="$HOME/.config/whisper-hotkey/whisper-hotkey.env"
if [[ ! -f "$ENV_FILE" ]]; then
  printf '%s\n' \
    '# Whisper hotkey configuration overrides' \
    '# WHISPER_SOCKET_PATH=/run/whisper/whisper.sock' \
    '# WHISPER_MODEL=base.en' \
    > "$ENV_FILE"
fi

systemctl --user daemon-reload

if [[ "$ENABLE_SERVICE" -eq 1 ]]; then
  systemctl --user enable --now whisper-hotkey.service
fi

echo "Installed easy-local-whisper-hotkey."
echo "Next steps:"
echo "  1. Start the Docker inference container: docker compose up -d"
echo "  2. Run: easy-local-whisper-hotkey doctor"
echo "  3. Optionally enable the service: systemctl --user enable --now whisper-hotkey.service"
