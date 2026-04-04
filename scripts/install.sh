#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENABLE_SERVICE=0
WHEEL_PATH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --enable-service)
      ENABLE_SERVICE=1
      shift
      ;;
    *)
      WHEEL_PATH="$1"
      shift
      ;;
  esac
done

if [[ -z "$WHEEL_PATH" ]]; then
  WHEEL_PATH="$(find "$ROOT_DIR/dist" -maxdepth 1 -name 'whisper_hotkey-*.whl' | sort | tail -n 1 || true)"
fi

if [[ -z "$WHEEL_PATH" || ! -f "$WHEEL_PATH" ]]; then
  echo "No wheel found. Build one first with scripts/build_release_assets.sh." >&2
  exit 1
fi

if command -v pipx >/dev/null 2>&1; then
  pipx install --force "$WHEEL_PATH"
else
  python3 -m pip install --user --force-reinstall "$WHEEL_PATH"
fi

mkdir -p "$HOME/.config/systemd/user"
mkdir -p "$HOME/.config/whisper-hotkey"
mkdir -p "$HOME/.local/share/whisper-hotkey/models"

cp "$ROOT_DIR/packaging/systemd/whisper-hotkey.service" "$HOME/.config/systemd/user/whisper-hotkey.service"

ENV_FILE="$HOME/.config/whisper-hotkey/whisper-hotkey.env"
if [[ ! -f "$ENV_FILE" ]]; then
  printf '%s\n' \
    '# Example overrides for whisper-hotkey' \
    '# WHISPER_CLI=/path/to/whisper-cli' \
    '# WHISPER_MODEL=/home/you/.local/share/whisper-hotkey/models/ggml-base.en.bin' \
    '# WHISPER_PREFERRED_SOURCES=alsa_input.usb-Razer_Inc_Razer_Seiren_Mini,alsa_input.usb-Anker_PowerConf_C200' \
    > "$ENV_FILE"
fi

systemctl --user daemon-reload

if [[ "$ENABLE_SERVICE" -eq 1 ]]; then
  systemctl --user enable --now whisper-hotkey.service
fi

echo "Installed whisper-hotkey."
echo "Next steps:"
echo "  1. Put a GGML model at ~/.local/share/whisper-hotkey/models/ggml-base.en.bin or set WHISPER_MODEL."
echo "  2. Ensure whisper-cli is on PATH or set WHISPER_CLI."
echo "  3. Run: whisper-hotkey doctor"
echo "  4. Optionally enable the service with: systemctl --user enable --now whisper-hotkey.service"
