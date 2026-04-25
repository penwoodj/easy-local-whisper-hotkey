# Playwright E2E Test Plan for Whisper Hotkey Web UI

## Overview

This document defines comprehensive end-to-end tests for the standalone React web UI using Playwright in headless mode. Tests verify all user flows work correctly: configuration changes, daemon control, diagnostics, and error handling.

## Test Environment

**Backend:** FastAPI server running on localhost:8420
**Frontend:** Vite dev server on localhost:5173 (with API proxy)
**Browser:** Chromium headless mode

## Setup Commands

### Start Backend
```bash
cd /home/jon/code/easy-local-whisper-hotkey
python -m uvicorn whisper_hotkey.api:app --host 127.0.0.0.1 --port 8420
```

### Start Frontend
```bash
cd /home/jon/code/easy-local-whisper-hotkey/web-ui
npm run dev
```

### Run Playwright Tests
```bash
cd /home/jon/code/easy-local-whisper-hotkey
python tests/e2e/qa_webui.py
```

## Test Categories

### 1. Application Startup and Navigation

**Test: Page Loads Successfully**
- Navigate to http://localhost:5173
- Wait for networkidle
- Verify h1 text: "Whisper Hotkey Control"
- Verify no console errors
- Verify status tab is active by default

**Test: Tab Navigation**
- Click "Configuration" tab
- Verify configuration content appears, status content hides
- Click "Diagnostics" tab
- Verify diagnostics content appears, configuration content hides
- Click back to "Status" tab
- Verify status content re-appears

### 2. Status Tab - Daemon Control

**Test: Load Initial Status**
- On page load, verify daemon status displays correctly (Running or Stopped)
- Verify status color: green for running, red for stopped
- Verify PID shows if running, hidden if stopped

**Test: Start Daemon**
- If daemon stopped, click "Start Daemon" button
- Verify button text changes to disabled state
- Verify loading indicator appears
- Wait 5 seconds
- Verify status changes to "Running" with green color
- Verify PID appears
- Verify button changes to "Stop Daemon"

**Test: Stop Daemon**
- If daemon running, click "Stop Daemon" button
- Verify button disabled state
- Verify loading indicator
- Wait 3 seconds
- Verify status changes to "Stopped" with red color
- Verify PID hides

**Test: Real-Time Events (SSE)**
- Start daemon
- Watch SSE connection status (network tab in devtools)
- Verify stream_text updates when transcription occurs
- Verify no connection errors in console

### 3. Configuration Panel

**Test: Load Existing Config**
- Navigate to Configuration tab
- Verify all config fields populate from backend
- Verify WHISPER_CLI field shows path
- Verify WHISPER_MODEL shows model path
- Verify numeric fields show correct values (chunk_seconds, etc.)
- Verify boolean toggles show correct state (suppress_nst, etc.)

**Test: Edit Path Configuration**
- Change WHISPER_CLI to a different path
- Click "Save Configuration" button
- Verify success message appears
- Navigate away and back to Configuration tab
- Verify WHISPER_CLI shows new value
- Check backend env file (~/.config/whisper-hotkey/whisper-hotkey.env) to verify write

**Test: Edit Numeric Configuration**
- Modify WHISPER_CHUNK_SECONDS to 5.0
- Modify WHISPER_TYPE_DELAY_MS to 50
- Save configuration
- Verify values persist after reload
- Verify validation (no negative numbers allowed)

**Test: Edit Boolean Toggles**
- Toggle SUPPRESS_NST to false
- Toggle SMART_PUNCTUATION to false
- Toggle SYMBOL_WORDS_TO_SYMBOLS to true
- Save configuration
- Verify toggles remain in new state after reload

**Test: Edit Dropdown Selections**
- Change WHISPER_LANGUAGE from "en" to "es"
- Change ACTIVATION_MODE from "toggle" to "hold"
- Save configuration
- Verify selections persist

**Test: Validation Errors**
- Set WHISPER_CHUNK_SECONDS to -1
- Attempt save
- Verify error message appears: "Invalid value for WHISPER_CHUNK_SECONDS"
- Verify save does not succeed
- Fix value to valid number
- Verify save succeeds

**Test: Config Save Error Handling**
- Stop backend server
- Attempt configuration save
- Verify error message: "Failed to save config: Connection refused"
- Restart backend
- Verify save succeeds

### 4. Audio Source Management

**Test: Load Audio Sources**
- Click "Refresh Sources" button
- Verify sources list populates
- Verify default source is marked

**Test: Select Audio Source**
- Select different source from dropdown
- Save configuration
- Verify source persists

**Test: Source Error Handling**
- Set invalid audio source
- Verify diagnostics shows "resolved_source_error"
- Verify configuration shows error indicator

### 5. Diagnostics Panel

**Test: Load Diagnostics**
- Navigate to Diagnostics tab
- Verify all system info displays
- Verify model_exists status
- Verify whisper_cli_exists status
- Verify commands status (parec, pactl, xdotool)
- Verify display environment variables

**Test: Health Check**
- Click "Run Health Check" button
- Verify healthy boolean reflects actual state
- If any check fails, verify red indicator

**Test: Audio Source Diagnostics**
- Verify available_sources list populates
- Verify resolved_source shows if valid
- Verify source_error displays if resolution fails

### 6. Error Display and Recovery

**Test: Network Errors**
- Stop backend server
- Trigger any action requiring backend (status refresh, config load)
- Verify error banner appears with red background
- Verify error message is descriptive
- Restart backend
- Click refresh button
- Verify error banner disappears

**Test: Connection Loss Recovery**
- While backend running, stop it
- Wait 10 seconds
- Restart backend
- Click "Refresh Status"
- Verify app reconnects and loads current state

### 7. Browser Compatibility

**Test: Chrome/Chromium**
- Run all tests in Chromium headless
- Verify all tests pass

**Test: Firefox**
- Run all tests in Firefox headless (if supported)
- Note any rendering differences

### 8. Responsive Design

**Test: Desktop View**
- Resize browser to 1920x1080
- Verify all controls visible and accessible

**Test: Small Window**
- Resize browser to 1024x768
- Verify layout does not break
- Verify tabs still functional
- Verify scrollbars appear for long content

## Bug Reporting Template

When a bug is found, document it with this format:

```markdown
### Bug: [Short description]

**Severity:** (Critical/High/Medium/Low)
**Steps to Reproduce:**
1. Step 1
2. Step 2
3. ...

**Expected Behavior:** (What should happen)
**Actual Behavior:** (What actually happens)

**Environment:**
- Backend: (FastAPI version, Python version)
- Frontend: (React version, browser)
- OS: (Linux distribution)

**Error Logs:** (Console errors, network failures)

**Workaround:** (If any)
```

## Priority Tests

**Must Pass:**
- All 3 navigation tests
- Start/Stop daemon tests
- Configuration save/load tests
- Error handling tests

**Important:**
- Audio source selection
- Diagnostics load
- SSE event connection

**Nice to Have:**
- All configuration field types validated
- Responsive design tested thoroughly
- Cross-browser compatibility

## Continuous Testing

After any code changes:
1. Run Playwright test suite
2. Fix any failing tests before proceeding
3. Document new bugs found
4. Update test plan with edge cases discovered
