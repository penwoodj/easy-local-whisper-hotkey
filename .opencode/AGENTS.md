# Workspace Rules — easy-local-whisper-hotkey

## Verification Gate: No "Done" Without Evidence

NEVER claim task completion without running verification commands and confirming output.

### Required Checks Before "Done"

**After any frontend (React/TypeScript) changes:**
```bash
cd tauri-app && npm run build
cd tauri-app && npx vitest run
```
Both MUST exit 0. Zero type errors, zero test failures.

**After any Rust changes:**
```bash
cd tauri-app/src-tauri && cargo build
cd tauri-app/src-tauri && cargo test --lib
```
Both MUST exit 0.

**After any Python changes:**
```bash
PYTHONPATH=src python -m unittest discover -s tests/unit -t . -p 'test_*.py' -v
```
All tests MUST pass. Pre-existing failures must be documented, not ignored.

**After changes to daemon/indicator/audio pipeline (indicator.py, app.py, postprocessor.py):**
```bash
./scripts/smoke_test.sh
```
All smoke test checks MUST pass. Requires test audio at `/tmp/whisper_test_sample.wav` — record with:
```bash
arecord -d 5 -f S16_LE -r 16000 -c 1 /tmp/whisper_test_sample.wav
```

**After daemon changes, restart the daemon and verify it's alive:**
```bash
pkill -f "whisper.hotkey" 2>/dev/null; rm -f /tmp/whisper_hotkey.lock
nohup .venv/bin/python -m whisper_hotkey > /dev/null 2>&1 &
sleep 3 && tail -5 /tmp/whisper_hotkey.log
# MUST show "Daemon ready" in last log line
```

**After any Tauri plugin or Cargo.toml changes:**
```bash
cd tauri-app && NO_STRIP=1 npm run tauri build
```
Must produce deb/rpm/AppImage without errors.

### What Counts as Evidence

- `lsp_diagnostics` clean on changed files (zero errors)
- Build command exits 0
- Test suite passes (all green)
- Smoke test passes (see below)
- Manual verification only when automated tests cannot cover (e.g., visual UI, X11 hotkeys)

### What Does NOT Count

- "Looks correct" without running build
- "Should work" without running tests
- Skipping verification because "changes are trivial"
- Marking todo complete before evidence collected

### Pre-existing Known Issues

These are documented bugs in source files — do NOT fix unless explicitly asked:
- `src/whisper_hotkey/cli.py` missing `import json` — breaks `test_print_config_json`
- `src/whisper_hotkey/cli.py` `load_env_file()` has inverted logic bug — always returns `{}`

## Runtime Validation Criteria

Build + tests passing is NOT sufficient. These checks catch issues that unit tests miss:

### CR1: Tauri Window Sizing Sanity
- `tauri.conf.json` `width/height` must be within `minWidth/maxWidth` bounds
- `useWindowResize.ts` tab sizes must not exceed `tauri.conf.json` `maxHeight`
- Initial window size must be usable (not too small for content)
- Config tab MUST have enough height for all 7 collapsible sections (600px+)

### CR2: Body Overflow / Scrollability
- `body { overflow: hidden }` MUST NOT be set — it blocks ALL scroll in the app
- Use `#root { overflow: hidden }` instead if needed for layout containment
- Every tab with scrollable content MUST have a `scroll-container` class with `overflow-y: auto`
- Config panel (longest tab) MUST scroll — verify by rendering all sections open

### CR3: isTauri() Guards on API Calls
- Every component using `invoke()`, `open()`, `homeDir()`, `getCurrentWindow()` MUST guard with `isTauri()`
- Tests for these components MUST set `window.__TAURI_INTERNALS__ = {}` in `beforeEach`
- Tests MUST clean up with `delete (window as any).__TAURI_INTERNALS__` in `afterEach`
- Without the guard, components crash in dev mode (vite dev without Tauri backend)

### CR4: PhysicalSize vs LogicalSize
- Use `LogicalSize` (NOT `PhysicalSize`) for window resize — PhysicalSize breaks on HiDPI/retina
- `PhysicalSize(300, 600)` on a 2x display = 150x300 logical pixels (tiny window)
- `LogicalSize(300, 600)` = 300x600 logical pixels regardless of DPI scaling

### CR5: CollapsibleSection Rendering
- `<details>` children must always be in DOM (not conditional rendered) — test queries need them
- Use CSS visibility or `<details>` native toggle, not `{isOpen && children}`
- Arrow rotation must be driven by React state, not CSS `group-open` (unreliable with controlled open)

### CR6: CSS Layout Constraints
- Every scrollable area needs `padding-right: 8px+` to prevent scrollbar overlap with content
- `h-screen` / `w-screen` on root is fine, but children with `flex-1` need `overflow-y: auto` or `min-h-0`
- Footer must use `shrink-0` to prevent being crushed when content overflows

### Test Commands Quick Reference

| Layer    | Command                                                            | Expected       |
|----------|--------------------------------------------------------------------|----------------|
| React    | `cd tauri-app && npx vitest run`                                   | 112 pass       |
| React coverage | `cd tauri-app && npx vitest run --coverage`                  | Check thresholds |
| Rust     | `cd tauri-app/src-tauri && cargo test --lib`                       | 23 pass        |
| Rust build | `cd tauri-app/src-tauri && cargo build`                          | Exit 0         |
| Python   | `PYTHONPATH=src python -m unittest discover -s tests/unit -t . -p 'test_*.py' -v` | 147 pass |
| Tauri    | `cd tauri-app && NO_STRIP=1 npm run tauri build`                   | Exit 0         |
| TS build | `cd tauri-app && npm run build`                                    | Exit 0         |
| Smoke    | `./scripts/smoke_test.sh`                                          | All pass       |

## Runtime Service Verification

### Audio Test Sample

Test audio file lives at `/tmp/whisper_test_sample.wav`. Create it by having the user run:
```bash
arecord -d 5 -f S16_LE -r 16000 -c 1 /tmp/whisper_test_sample.wav
```
Expected content: "testing testing one two three"

### Daemon Health Check

After ANY change to the daemon service (app.py, indicator.py, postprocessor.py):

1. Kill old process: `pkill -f "whisper.hotkey" 2>/dev/null; rm -f /tmp/whisper_hotkey.lock`
2. Start fresh: `nohup .venv/bin/python -m whisper_hotkey > /dev/null 2>&1 &`
3. Wait 3s then check: `tail -10 /tmp/whisper_hotkey.log`
4. MUST see "Daemon ready" and "CaretTracker: AT-SPI listener started" without errors
5. MUST see process alive: `ps aux | grep whisper | grep -v grep`

### Transcription Pipeline Check

When testing audio pipeline without the daemon:
```bash
.venv/bin/python -c "
import sys, wave, struct
sys.path.insert(0, 'src')
import numpy as np
from faster_whisper import WhisperModel
model = WhisperModel('base.en', device='cpu', compute_type='int8',
                     download_root='/home/jon/.config/com.pais.handy/models/')
with wave.open('/tmp/whisper_test_sample.wav', 'rb') as w:
    frames = w.readframes(w.getnframes())
samples = struct.unpack('<' + 'h' * (len(frames) // 2), frames)
audio = np.array(samples, dtype=np.float32) / 32768.0
segments, _ = model.transcribe(audio, language='en', vad_filter=True)
text = ' '.join(s.text.strip() for s in segments if s.text.strip())
print(f'TRANSCRIPT: {text!r}')
assert 'testing' in text.lower() or 'one' in text.lower(), f'Transcription failed: {text!r}'
print('PASS')
"
```

### X11 Indicator Check

When testing indicator changes:
```bash
.venv/bin/python -c "
import ctypes, time, sys
sys.path.insert(0, 'src')
from whisper_hotkey.indicator import CursorIndicator, CaretTracker
from whisper_hotkey.app import Logger
from pathlib import Path
libx11 = ctypes.cdll.LoadLibrary('libX11.so.6')
libx11.XOpenDisplay.argtypes = [ctypes.c_char_p]
libx11.XOpenDisplay.restype = ctypes.c_void_p
libx11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
libx11.XDefaultRootWindow.restype = ctypes.c_ulong
d = libx11.XOpenDisplay(None)
r = libx11.XDefaultRootWindow(d)
logger = Logger(Path('/tmp/whisper_indicator_check.log'))
tracker = CaretTracker(logger=logger)
tracker.start()
ind = CursorIndicator(libx11=libx11, display=d, root_window=r, logger=logger, caret_tracker=tracker)
ind.show()
time.sleep(1)
print('Indicator visible for 1s')
ind.hide()
ind.destroy()
tracker.stop()
print('PASS')
"
```
