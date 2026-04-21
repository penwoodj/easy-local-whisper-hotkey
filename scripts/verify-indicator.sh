#!/usr/bin/env bash
set -euo pipefail

if ! command -v xdotool >/dev/null 2>&1 && ! command -v xwininfo >/dev/null 2>&1; then
    echo "Error: Neither xdotool nor xwininfo found"
    exit 1
fi

echo "=== X11 Indicator Window Verification ==="

if [ -n "$DISPLAY" ]; then
    echo "Display: $DISPLAY"
else
    echo "Error: DISPLAY not set"
    exit 1
fi

if command -v xwininfo >/dev/null 2>&1; then
    WINDOW_ID=$(xwininfo -root -tree | grep -i "whisper" | head -1 | awk '{print $1}' || true)

    if [ -n "$WINDOW_ID" ]; then
        echo "Found indicator window: $WINDOW_ID"

        if xwininfo -id "$WINDOW_ID" 2>/dev/null | grep -q "Map State: IsViewable"; then
            echo "Window is mapped and visible"
            xwininfo -id "$WINDOW_ID" 2>/dev/null | grep -E "(Absolute upper-left X|Absolute upper-left Y|Width|Height)"
            exit 0
        else
            echo "Window found but not mapped"
            exit 1
        fi
    else
        echo "No whisper indicator window found"
    fi
fi

if command -v xdotool >/dev/null 2>&1; then
    WINDOW_ID=$(xdotool search --name "whisper" 2>/dev/null | head -1 || true)

    if [ -n "$WINDOW_ID" ]; then
        echo "Found indicator window: $WINDOW_ID"

        if xdotool windowactivate "$WINDOW_ID" 2>/dev/null; then
            echo "Window is mapped and activatable"
            GEOMETRY=$(xdotool getwindowgeometry "$WINDOW_ID" 2>/dev/null || true)
            echo "$GEOMETRY"
            exit 0
        else
            echo "Window found but not activatable"
            exit 1
        fi
    else
        echo "No whisper indicator window found"
        exit 1
    fi
fi

exit 1
