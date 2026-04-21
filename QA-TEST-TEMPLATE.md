# QA Test Template — Easy Local Whisper Hotkey v0.1.0

**Date:** _______________
**Tester:** _______________
**OS/DE:** _______________ (e.g., Ubuntu 24.04 / GNOME / X11)
**Build:** _______________ (AppImage / deb / rpm / `npm run tauri dev`)
**AppImage path:** `tauri-app/src-tauri/target/release/bundle/appimage/Easy Local Whisper Hotkey_0.1.0_amd64.AppImage`

---

## Instructions

1. Launch the app using the build method above
2. Work through each section below
3. Mark each test: ✅ Pass | ❌ Fail | ⚠️ Partial | N/A (not applicable)
4. For failures, note what happened in the "Notes" column
5. Return completed template when done

---

## 1. Startup & Window

| # | Test | Result | Notes |
|---|------|--------|-------|
| 1.1 | App launches without crash | | |
| 1.2 | Window appears at correct size (~300×420) | | |
| 1.3 | Dark theme renders correctly | | |
| 1.4 | Three tabs visible: Status, Modes, Config | | |
| 1.5 | No console errors in terminal (if launched from CLI) | | |
| 1.6 | Second launch attempt focuses existing window (no duplicate) | | |

---

## 2. Status Tab

| # | Test | Result | Notes |
|---|------|--------|-------|
| 2.1 | Status tab shows on launch (default) | | |
| 2.2 | Canvas waveform element present | | |
| 2.3 | Start/Stop button visible and clickable | | |
| 2.4 | "Stopped" text shown when idle | | |
| 2.5 | Footer shows Ctrl+Space shortcut | | |
| 2.6 | Footer shows Ctrl+Shift+Alt+Space shortcut | | |
| 2.7 | Toggle/Hold mode label visible in footer | | |
| 2.8 | Clicking Start attempts daemon launch (may fail if Python not installed) | | |
| 2.9 | Content area NOT black/blank | | |

---

## 3. Modes Tab

| # | Test | Result | Notes |
|---|------|--------|-------|
| 3.1 | Clicking Modes tab switches content | | |
| 3.2 | All 9 modes visible: Off, Light, Aggressive, Agentic, Writing, Code, Structure, Persona, Clarity | | |
| 3.3 | Clicking a mode highlights it (active state) | | |
| 3.4 | "Current: [mode]" label updates on selection | | |
| 3.5 | Radiogroup role present (accessibility) | | |
| 3.6 | Mode descriptions visible (e.g., "No processing", "Punctuation only", "Full grammar fix") | | |
| 3.7 | Content area NOT black/blank | | |

---

## 4. Config Tab (CRITICAL — WebKitGTK Black Screen Fix)

> **This is the most important test section.** The bug was: config tab showed a black/blank screen in WebKitGTK (Tauri AppImage on Linux). The fix removed opacity animations and 100vh/100vw CSS.

| # | Test | Result | Notes |
|---|------|--------|-------|
| 4.1 | Clicking Config tab shows content (NOT black/blank) | | |
| 4.2 | Config loads without visible delay/flash | | |
| 4.3 | All 7 collapsible sections visible (headers) | | |
| 4.4 | Sections: Audio & Transcription, Audio Source, Streaming Behavior, Features, Post-Processing, Voice Control, Advanced | | |
| 4.5 | Clicking section header expands/collapses it | | |
| 4.6 | Input fields render (not invisible/overlapping) | | |
| 4.7 | Switch toggles render and are clickable | | |
| 4.8 | Scrollbar does NOT overlap/cover input fields | | |
| 4.9 | Whisper CLI path field visible | | |
| 4.10 | Model path field visible | | |
| 4.11 | Language field visible | | |
| 4.12 | Audio source field visible | | |
| 4.13 | Chunk seconds field visible | | |
| 4.14 | Real-time switch visible | | |
| 4.15 | Smart Punctuation switch visible | | |
| 4.16 | Post-Processing section expandable | | |
| 4.17 | Voice Control section expandable | | |
| 4.18 | RulesManager present ("Remove filler words" text) | | |
| 4.19 | Log File field visible | | |
| 4.20 | No inline 100vh/100vw viewport units in rendered page | | |

---

## 5. Tab Switching

| # | Test | Result | Notes |
|---|------|--------|-------|
| 5.1 | Switch Status → Modes: content updates correctly | | |
| 5.2 | Switch Modes → Config: content visible (NOT black) | | |
| 5.3 | Switch Config → Status: content updates correctly | | |
| 5.4 | Switch Status → Config → Status: no rendering artifacts | | |
| 5.5 | Rapid switching (5 times fast): no crashes/black screens | | |
| 5.6 | Window resizes correctly per tab (if dynamic sizing implemented) | | |

---

## 6. CSS & Rendering (WebKitGTK Compatibility)

| # | Test | Result | Notes |
|---|------|--------|-------|
| 6.1 | `#root` has `position: absolute` (not height: 100vh) | | |
| 6.2 | No `tab-content` class with fadeIn animation anywhere | | |
| 6.3 | No `opacity: 0` on any visible content | | |
| 6.4 | All content opacity = 1 (fully visible) | | |
| 6.5 | No blank divs > 50px height with no content | | |
| 6.6 | Scroll container has adequate padding-right | | |

---

## 7. Error Handling

| # | Test | Result | Notes |
|---|------|--------|-------|
| 7.1 | If config fails to load, error message shown (not blank) | | |
| 7.2 | No JavaScript console errors | | |
| 7.3 | No Rust panic messages in terminal | | |
| 7.4 | App remains responsive after error | | |

---

## 8. Daemon Integration (if Python installed)

> Only test if `easy-local-whisper-hotkey` Python package is installed and `whisper-cli` is available.

| # | Test | Result | Notes |
|---|------|--------|-------|
| 8.1 | Start button launches daemon (PID shown) | | |
| 8.2 | Only ONE daemon process spawned (no duplicate windows) | | |
| 8.3 | Stop button kills daemon process | | |
| 8.4 | Ctrl+Space triggers recording (X11) | | |
| 8.5 | Recorded text appears in streaming area | | |
| 8.6 | Text typed into focused window (xdotool) | | |
| 8.7 | Mode change applies to next transcription | | |
| 8.8 | Config changes persist after restart | | |

---

## 9. Regression Tests

| # | Test | Result | Notes |
|---|------|--------|-------|
| 9.1 | AppImage builds without errors | | |
| 9.2 | React tests pass (124/124) | | |
| 9.3 | Rust tests pass (23/23) | | |
| 9.4 | Python tests pass (147/147) | | |
| 9.5 | Vite build succeeds | | |
| 9.6 | Tauri build succeeds (deb + AppImage) | | |

---

## Summary

| Category | Pass | Fail | N/A |
|----------|------|------|-----|
| 1. Startup & Window | /6 | | |
| 2. Status Tab | /9 | | |
| 3. Modes Tab | /7 | | |
| 4. Config Tab | /20 | | |
| 5. Tab Switching | /6 | | |
| 6. CSS & Rendering | /6 | | |
| 7. Error Handling | /4 | | |
| 8. Daemon Integration | /8 | | |
| 9. Regression Tests | /6 | | |
| **TOTAL** | **/72** | | |

### Blockers

List any issues that prevent normal use:

1. _______________________________________________
2. _______________________________________________
3. _______________________________________________

### General Notes

_______________________________________________
_______________________________________________
_______________________________________________
