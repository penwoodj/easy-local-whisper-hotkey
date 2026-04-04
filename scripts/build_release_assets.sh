#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VERSION="$(
  python3 - <<'PY'
from pathlib import Path

namespace = {}
exec(Path("src/whisper_hotkey/__init__.py").read_text(encoding="utf-8"), namespace)
print(namespace["__version__"])
PY
)"

python3 -m build --no-isolation

BUNDLE_DIR="dist/whisper-hotkey-${VERSION}"
rm -rf "$BUNDLE_DIR"
mkdir -p "$BUNDLE_DIR"

cp README.md LICENSE CHANGELOG.md "$BUNDLE_DIR"/
cp -R docs packaging "$BUNDLE_DIR"/

tar -czf "dist/whisper-hotkey-${VERSION}-bundle.tar.gz" -C dist "whisper-hotkey-${VERSION}"
rm -rf "$BUNDLE_DIR"

find dist -maxdepth 1 -type f ! -name "SHA256SUMS" -print0 \
  | sort -z \
  | xargs -0 sha256sum > dist/SHA256SUMS
