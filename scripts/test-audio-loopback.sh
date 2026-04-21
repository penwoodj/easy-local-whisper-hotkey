#!/usr/bin/env bash
set -euo pipefail

AUDIO_FILE="${1:-/tmp/whisper_test_sample.wav}"

echo "=== Audio Loopback Test ==="

if [ ! -f "$AUDIO_FILE" ]; then
    echo "Error: Audio file not found: $AUDIO_FILE"
    echo "Create one with: arecord -d 5 -f S16_LE -r 16000 -c 1 $AUDIO_FILE"
    exit 1
fi

if ! command -v paplay >/dev/null 2>&1; then
    echo "Error: paplay not found"
    exit 1
fi

SIZE=$(stat -c%s "$AUDIO_FILE" 2>/dev/null || echo 0)
echo "Audio file: $AUDIO_FILE (${SIZE} bytes)"

if [ "$SIZE" -lt 10000 ]; then
    echo "Error: Audio file too small"
    exit 1
fi

echo "Testing playback with paplay..."

timeout 10 paplay --raw --format=s16le --rate=16000 --channels=1 "$AUDIO_FILE" 2>&1 || {
    echo "Error: paplay failed"
    exit 1
}

echo "Playback completed successfully"
exit 0
