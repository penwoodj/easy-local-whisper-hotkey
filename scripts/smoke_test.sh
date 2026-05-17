#!/usr/bin/env bash
set -euo pipefail

# Smoke test for whisper-hotkey daemon
# Usage: ./scripts/smoke_test.sh [/path/to/test_audio.wav]
#
# If no audio file provided, uses /tmp/whisper_test_sample.wav
# Expects the audio to contain "testing testing one two three"

AUDIO="${1:-/tmp/whisper_test_sample.wav}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${REPO_ROOT}/.venv/bin/python"
LOCK="/tmp/whisper_hotkey.lock"
TIMEOUT=30

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}PASS${NC}: $1"; }
fail() { echo -e "${RED}FAIL${NC}: $1"; }
warn() { echo -e "${YELLOW}WARN${NC}: $1"; }

echo "=== Whisper Hotkey Smoke Test ==="
echo "Audio: $AUDIO"
echo ""

# T1: Test audio file exists
if [ -f "$AUDIO" ]; then
    SIZE=$(stat -c%s "$AUDIO" 2>/dev/null || echo 0)
    if [ "$SIZE" -gt 10000 ]; then
        pass "Audio file exists (${SIZE} bytes)"
    else
        fail "Audio file too small (${SIZE} bytes)"
        exit 1
    fi
else
    fail "Audio file not found: $AUDIO"
    echo "Record one with: arecord -d 5 -f S16_LE -r 16000 -c 1 $AUDIO"
    exit 1
fi

# T2: Python imports work
echo "--- Testing Python imports ---"
$VENV -c "
import sys; sys.path.insert(0, 'src')
from whisper_hotkey.app import X11HotkeyDaemon, Recorder, Transcriber, Logger
from whisper_hotkey.indicator import CursorIndicator, CaretTracker
print('All imports OK')
" 2>&1 && pass "Python imports" || { fail "Python imports"; exit 1; }

# T3: faster-whisper loads
echo "--- Testing faster-whisper model load ---"
$VENV -c "
import sys; sys.path.insert(0, 'src')
from faster_whisper import WhisperModel
model = WhisperModel('base.en', device='cpu', compute_type='int8',
                     download_root='\${HOME}/.local/share/whisper-hotkey/models')
print('faster-whisper loaded OK')
" 2>&1 && pass "faster-whisper model" || fail "faster-whisper model (may need download)"

# T4: Transcribe the test audio file
echo "--- Testing transcription pipeline ---"
TRANSCRIPT=$($VENV -c "
import sys, wave, os, tempfile
sys.path.insert(0, 'src')
import numpy as np
from faster_whisper import WhisperModel

audio_path = '$AUDIO'
model = WhisperModel('base.en', device='cpu', compute_type='int8',
                     download_root='\${HOME}/.local/share/whisper-hotkey/models')

# Read wav file
with wave.open(audio_path, 'rb') as w:
    frames = w.readframes(w.getnframes())

import struct
samples = struct.unpack('<' + 'h' * (len(frames) // 2), frames)
audio = np.array(samples, dtype=np.float32) / 32768.0

segments, info = model.transcribe(audio, language='en', vad_filter=True)
text = ' '.join(s.text.strip() for s in segments if s.text.strip())
print(text)
" 2>&1) || TRANSCRIPT=""

echo "Transcript: '$TRANSCRIPT'"
if echo "$TRANSCRIPT" | grep -qi "testing\|one\|two\|three"; then
    pass "Transcription produced recognizable text"
else
    fail "Transcription did not contain expected words"
fi

# T5: AT-SPI caret tracker can start
echo "--- Testing AT-SPI caret tracker ---"
$VENV -c "
import sys, time, threading
sys.path.insert(0, 'src')
from whisper_hotkey.indicator import CaretTracker
from whisper_hotkey.app import Logger
from pathlib import Path

logger = Logger(Path('/tmp/whisper_smoke_atspi.log'))
tracker = CaretTracker(logger=logger)
tracker.start()
time.sleep(2)
pos = tracker.get_position()
tracker.stop()
if pos:
    print(f'Caret position: {pos}')
else:
    print('No caret position (normal if no text field focused)')
print('AT-SPI tracker OK')
" 2>&1 && pass "AT-SPI CaretTracker" || warn "AT-SPI CaretTracker (may need accessibility bus)"

# T6: X11 indicator window can be created
echo "--- Testing X11 indicator ---"
$VENV -c "
import ctypes, time, sys
sys.path.insert(0, 'src')
from whisper_hotkey.indicator import CursorIndicator
from whisper_hotkey.app import Logger
from pathlib import Path

libx11 = ctypes.cdll.LoadLibrary('libX11.so.6')
libx11.XOpenDisplay.argtypes = [ctypes.c_char_p]
libx11.XOpenDisplay.restype = ctypes.c_void_p
libx11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
libx11.XDefaultRootWindow.restype = ctypes.c_ulong

display = libx11.XOpenDisplay(None)
if not display:
    print('ERROR: cannot open display')
    sys.exit(1)
root = libx11.XDefaultRootWindow(display)

logger = Logger(Path('/tmp/whisper_smoke_indicator.log'))
indicator = CursorIndicator(libx11=libx11, display=display, root_window=root, logger=logger)
indicator.show()
time.sleep(0.5)
indicator.hide()
indicator.destroy()
print('Indicator window created and destroyed OK')
" 2>&1 && pass "X11 indicator window" || fail "X11 indicator window"

# T7: Service can start (launch briefly, check logs)
echo "--- Testing daemon startup ---"
rm -f "$LOCK"
rm -f /tmp/whisper_hotkey.log
$VENV -m whisper_hotkey > /dev/null 2>&1 &
DAEMON_PID=$!
sleep 4

DAEMON_LOG="/tmp/whisper_hotkey.log"

if kill -0 $DAEMON_PID 2>/dev/null; then
    pass "Daemon started (PID $DAEMON_PID)"
    kill $DAEMON_PID 2>/dev/null
    wait $DAEMON_PID 2>/dev/null
else
    fail "Daemon failed to start"
    cat "$DAEMON_LOG" 2>/dev/null
fi

# T8: Check daemon logs for CaretTracker
echo "--- Checking daemon logs ---"
if grep -q "CaretTracker: AT-SPI listener started" "$DAEMON_LOG" 2>/dev/null; then
    pass "CaretTracker started in daemon"
else
    warn "CaretTracker log not found (check $DAEMON_LOG)"
fi

if grep -q "Daemon ready" "$DAEMON_LOG" 2>/dev/null; then
    pass "Daemon reached ready state"
else
    fail "Daemon did not reach ready state"
fi

echo ""
echo "=== Smoke test complete ==="
