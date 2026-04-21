# Keyboard Shortcuts Audit Report

**Date:** 2026-04-19  
**Project:** easy-local-whisper-hotkey  
**Severity:** HIGH  
**Component:** Keyboard Shortcut Handling (X11 Key Grabs, UI Display, CLI Forwarding)

---

## Executive Summary

The keyboard shortcut system has three components: X11 key grabs in the Python daemon, UI display in the Tauri frontend, and CLI flag forwarding. The X11 key grabs are correctly implemented for both `Ctrl+Space` (record toggle) and `Ctrl+Shift+Alt+Space` (mode cycling). DISPLAY is properly passed from Tauri to the daemon subprocess. However, `forwarded_runtime_args()` in `cli.py` does NOT forward `--activation-mode` or `--postprocess*` flags, meaning these settings can only reach the daemon via the env file.

---

## X11 Key Registration (Python Daemon)

### Key Constants (app.py:45-67)

```python
KEY_PRESS = 2
KEY_RELEASE = 3
GRAB_MODE_ASYNC = 1
CONTROL_MASK = 0x4
LOCK_MASK = 0x2
MOD2_MASK = 0x10
MOD5_MASK = 0x80
SHIFT_MASK = 0x1
MOD1_MASK = 0x8
XK_SPACE = 0x20
XK_CONTROL_L = 0xFFE3
XK_CONTROL_R = 0xFFE4
XK_SHIFT_L = 0xFFE1
XK_SHIFT_R = 0xFFE2
XK_ALT_L = 0xFFE9
XK_ALT_R = 0xFFEA
XK_M = 0x6D
XK_NUM_LOCK = 0xFF7F
```

### Shortcut 1: Ctrl+Space (Record Toggle/Hold)

**Registration** (app.py:1108-1116):
```python
self.libx11.XGrabKey(
    self.display,
    int(self.space_keycode),     # XK_SPACE = 0x20
    modifiers,                   # CONTROL_MASK + Lock/NumLock variants
    self.root,
    0,
    GRAB_MODE_ASYNC,
    GRAB_MODE_ASYNC,
)
```

**Modifier variants registered:**
- `CONTROL_MASK`
- `CONTROL_MASK | LOCK_MASK`
- `CONTROL_MASK | numlock_mask`
- `CONTROL_MASK | LOCK_MASK | numlock_mask`
- `CONTROL_MASK | MOD2_MASK`
- `CONTROL_MASK | MOD5_MASK`
- ... etc for all NumLock/CapsLock combinations

### Shortcut 2: Ctrl+Shift+Alt+Space (Mode Cycling)

**Registration** (app.py:1127-1135):
```python
mode_modifiers_base = CONTROL_MASK | SHIFT_MASK | MOD1_MASK
# ... variant generation ...
self.libx11.XGrabKey(
    self.display,
    int(self.space_keycode),     # XK_SPACE = 0x20
    modifiers,                   # CONTROL_MASK | SHIFT_MASK | MOD1_MASK + variants
    self.root,
    0,
    GRAB_MODE_ASYNC,
    GRAB_MODE_ASYNC,
)
```

**This is correct.** MOD1_MASK (0x8) = Alt key. The modifier combination matches the UI display.

### Event Loop (app.py:1242-1268)

```python
event = XEvent()
while self.running:
    if self.libx11.XPending(self.display) == 0:
        time.sleep(0.05)
        continue
    
    self.libx11.XNextEvent(self.display, ctypes.byref(event))
    # ... dispatch based on event.type and keycodes
```

**Keycode tracking** (app.py:1055-1060):
```python
self.space_keycode = self.libx11.XKeysymToKeycode(self.display, XK_SPACE)
self.control_left_keycode = self.libx11.XKeysymToKeycode(self.display, XK_CONTROL_L)
self.control_right_keycode = self.libx11.XKeysymToKeycode(self.display, XK_CONTROL_R)
self.shift_left_keycode = self.libx11.XKeysymToKeycode(self.display, XK_SHIFT_L)
self.shift_right_keycode = self.libx11.XKeysymToKeycode(self.display, XK_SHIFT_R)
self.m_keycode = self.libx11.XKeysymToKeycode(self.display, XK_M)
```

**Note:** `m_keycode` (XK_M = 0x6D) is resolved but NOT used in any XGrabKey call. It may be leftover from an earlier shortcut design.

---

## UI Display (Tauri Frontend)

### App.tsx Footer (lines 230-246)

```tsx
<div className="shrink-0 px-4 py-2">
  <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 text-[10px] text-muted-foreground">
    <span className="flex items-center gap-1">
      <kbd>Ctrl+Space</kbd>
      {config?.voice_activation_mode === 'toggle' ? 'Toggle' : 'Hold'}
    </span>
    <span>•</span>
    <span className="flex items-center gap-1">
      <kbd>Ctrl+Shift+Alt+Space</kbd>
      Modes
    </span>
  </div>
</div>
```

**Assessment:** ✅ Correct. The UI shows:
- `Ctrl+Space` → Toggle or Hold (based on voice_activation_mode)
- `Ctrl+Shift+Alt+Space` → Mode cycling

These match the X11 key grab registrations.

---

## Tauri → Daemon Environment Passing

### start_daemon (commands.rs:478-508)

```rust
pub fn start_daemon(app_handle: AppHandle) -> Result<(), String> {
    // ...
    let child = Command::new("easy-local-whisper-hotkey")
        .arg("run")
        .env("WHISPER_CONFIG_ENV_FILE", config_path.to_string_lossy().to_string())
        .env("DISPLAY", env::var("DISPLAY").unwrap_or_else(|_| ":0".to_string()))
        .spawn()
        .map_err(|e| format!("Failed to start daemon: {}", e))?;
    // ...
}
```

**Assessment:** ✅ DISPLAY is passed with fallback to `:0`. This was previously missing and has been fixed.

---

## CLI Flag Forwarding Gap

### forwarded_runtime_args() (cli.py:122-153)

**Forwarded flags:**
- `--whisper-cli`, `--model`, `--source`, `--preferred-sources`
- `--chunk-seconds`, `--overlap-seconds`, `--type-delay-ms`
- `--language`, `--log-file`
- `--suppress-regex` (conditional), `--suppress-nst` (conditional)
- `--smart-punctuation` (conditional), `--symbol-words-to-symbols` (conditional)
- `--direct-streaming` (conditional)

**NOT forwarded:**
- `--activation-mode` ← voice activation mode setting
- `--postprocess` ← post-processing enabled toggle
- `--postprocess-mode` ← post-processing mode selection
- `--postprocess-trigger` ← post-processing trigger selection
- `--indicator` ← cursor indicator toggle
- `--log-level` ← log verbosity setting

**Impact:** LOW. When launched from Tauri, the daemon reads config from the env file via `WHISPER_CONFIG_ENV_FILE`. The CLI forwarding path is only used when invoking `easy-local-whisper-hotkey run` directly with flags. The env file contains all settings including the ones not forwarded via CLI.

---

## Keyboard Shortcut Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   SHORTCUT FLOW (X11)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  X11 Server (XOrg/XWayland)                                     │
│  ┌──────────────────┐                                           │
│  │ XGrabKey         │                                           │
│  │ Space + Ctrl     │ → Record toggle/hold                     │
│  │ Space + Ctrl+    │                                           │
│  │   Shift+Alt      │ → Mode cycling                           │
│  └────────┬─────────┘                                           │
│           │ XNextEvent                                           │
│           ▼                                                      │
│  Python Daemon (app.py)                                          │
│  ┌──────────────────┐                                           │
│  │ Event Loop       │                                           │
│  │ KEY_PRESS:       │                                           │
│  │   Ctrl+Space     │ → Start/stop recording                   │
│  │   Ctrl+Shift+    │                                           │
│  │     Alt+Space    │ → Cycle post-processing mode             │
│  │ KEY_RELEASE:     │                                           │
│  │   (hold mode)    │ → Stop recording                         │
│  └──────────────────┘                                           │
│                                                                  │
│  Tauri UI (React)                                                │
│  ┌──────────────────┐                                           │
│  │ Footer Display   │                                           │
│  │ Ctrl+Space       │ → Shows "Toggle" or "Hold"              │
│  │ Ctrl+Shift+      │                                           │
│  │   Alt+Space      │ → Shows "Modes"                          │
│  └──────────────────┘                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Issues Found

| # | Severity | Issue | Status |
|---|----------|-------|--------|
| 1 | Low | `forwarded_runtime_args()` missing 6 flags | Open — env file fallback works |
| 2 | Low | `XK_M` (0x6D) resolved but unused | Open — dead code |
| 3 | Medium | `log_level` not in Python args | Open — see config-persistence-audit.md |

---

## Recommendations

### P2: Forward Missing CLI Args (Low Priority)

Add to `forwarded_runtime_args()` in `cli.py`:
```python
args.extend(["--activation-mode", namespace.activation_mode])
if namespace.postprocess:
    args.append("--postprocess")
args.extend(["--postprocess-mode", namespace.postprocess_mode])
args.extend(["--postprocess-trigger", namespace.postprocess_trigger])
if namespace.indicator:
    args.append("--indicator")
args.extend(["--log-level", namespace.log_level])
```

### P3: Remove Dead Code (Low Priority)

Remove or document the unused `m_keycode` and `XK_M` constant if no longer needed.

---

## Verification Plan

### Test 1: X11 Key Grab Verification

```bash
# Start daemon, verify key grabs
easy-local-whisper-hotkey run &
xdotool key Ctrl+Space  # Should start recording
xdotool key Ctrl+Space  # Should stop recording (toggle mode)
xdotool key Ctrl+Shift+Alt+Space  # Should cycle mode
kill %1
```

### Test 2: UI Shortcut Display

```bash
# Launch Tauri app, verify footer shows correct shortcuts
# Expected: "Ctrl+Space Toggle • Ctrl+Shift+Alt+Space Modes"
```

### Test 3: DISPLAY Propagation

```bash
# Launch via Tauri, verify daemon has DISPLAY
# Check with: ps eww <pid> | grep DISPLAY
```

---

**Report prepared by:** Automated Code Audit System  
**Review methodology:** Static code analysis, X11 key grab inspection, data flow tracing
