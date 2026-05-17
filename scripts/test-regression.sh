#!/usr/bin/env bash
set -euo pipefail

AUDIO_FILE="${1:-/tmp/whisper_test_sample.wav}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${REPO_ROOT}/.venv/bin/python"
EXPECTED="testing testing one two three"
THRESHOLD="${2:-0.7}"

echo "=== Regression Test ==="
echo "Audio: $AUDIO_FILE"
echo "Expected: $EXPECTED"
echo "Similarity threshold: $THRESHOLD"
echo ""

if [ ! -f "$AUDIO_FILE" ]; then
    echo "Error: Audio file not found: $AUDIO_FILE"
    exit 1
fi

TRANSCRIPT=$($VENV -c "
import sys
sys.path.insert(0, 'src')
import numpy as np
import wave, struct
from faster_whisper import WhisperModel

audio_path = '$AUDIO_FILE'
model = WhisperModel('base.en', device='cpu', compute_type='int8',
                     download_root='\${HOME}/.local/share/whisper-hotkey/models')

with wave.open(audio_path, 'rb') as w:
    frames = w.readframes(w.getnframes())

samples = struct.unpack('<' + 'h' * (len(frames) // 2), frames)
audio = np.array(samples, dtype=np.float32) / 32768.0

segments, info = model.transcribe(audio, language='en', vad_filter=True)
text = ' '.join(s.text.strip() for s in segments if s.text.strip())
print(text.strip().lower())
" 2>&1) || TRANSCRIPT=""

echo "Transcript: '$TRANSCRIPT'"

SIMILARITY=$($VENV -c "
import difflib
expected = '$EXPECTED'.lower()
actual = '$TRANSCRIPT'
seq = difflib.SequenceMatcher(None, expected, actual)
ratio = seq.ratio()
print(f'{ratio:.2f}')
" 2>&1) || SIMILARITY=0

echo "Similarity: $SIMILARITY"

PASS=$($VENV -c "
threshold = float('$THRESHOLD')
similarity = float('$SIMILARITY')
print(1 if similarity >= threshold else 0)
" 2>&1) || PASS=0

if [ "$PASS" -eq 1 ]; then
    echo "PASS: Similarity meets threshold ($THRESHOLD)"
    exit 0
else
    echo "FAIL: Similarity below threshold ($THRESHOLD)"
    exit 1
fi
