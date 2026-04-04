#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[1/5] Python compile checks"
python3 -m compileall src tests

echo "[2/5] Shell syntax checks"
bash -n scripts/build_release_assets.sh scripts/install.sh scripts/uninstall.sh

echo "[3/5] Unit and integration tests"
PYTHONPATH="$ROOT_DIR/src" python3 -m unittest discover -s tests -t . -p 'test_*.py' -v

echo "[4/5] CLI smoke checks"
PYTHONPATH="$ROOT_DIR/src" python3 -m whisper_hotkey --version
PYTHONPATH="$ROOT_DIR/src" python3 -m whisper_hotkey print-config --json

echo "[5/5] Doctor check"
if PYTHONPATH="$ROOT_DIR/src" python3 -m whisper_hotkey doctor --json; then
  echo "doctor: healthy"
else
  echo "doctor: expected to fail if model/audio sources are not provisioned on this machine"
fi
