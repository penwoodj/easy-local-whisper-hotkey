#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

HOOK_SOURCE="$PROJECT_ROOT/git-hooks/pre-commit"
HOOK_DEST="$PROJECT_ROOT/.git/hooks/pre-commit"

if [ -f "$HOOK_SOURCE" ]; then
    cp "$HOOK_SOURCE" "$HOOK_DEST"
    chmod +x "$HOOK_DEST"
    echo "Pre-commit hook installed to $HOOK_DEST"
else
    echo "Error: $HOOK_SOURCE not found"
    exit 1
fi
