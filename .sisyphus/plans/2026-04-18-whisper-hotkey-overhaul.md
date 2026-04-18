# Whisper Hotkey Overhaul — Multi-Phase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 5 critical bugs and overhaul the UI/UX of the easy-local-whisper-hotkey Tauri desktop app across 5 phases, each independently testable and mergeable.

**Architecture:** Branch from `main` → `dev`, then feature branches from `dev`. Each phase merges back to `dev` after manual confirmation. After all phases, delete all feature branches — only `main` and `dev` remain.

**Tech Stack:** Tauri 2.x, Rust, React, TypeScript, shadcn/ui, Tailwind CSS v4, Python daemon (X11)

---

## Branching Strategy

```
main
 └── dev (created from main, accumulates all phase merges)
      ├── fix/critical-backend           (Phase 1)
      ├── feat/status-page-redesign      (Phase 2)
      ├── feat/config-panel-overhaul     (Phase 3)
      ├── feat/modes-tab-polish          (Phase 4)
      └── feat/global-styling            (Phase 5)
```

- Create `dev` from `main` first
- Each phase creates its feature branch from `dev`
- After each phase: verify → merge to `dev` → delete feature branch
- After all phases: merge `dev` → `main`, delete all feature branches locally and on GitHub

---

## Phase 0: Critical Reviews (Already Complete)

Audit reports written to `docs/reports/critical-reviews/`:
1. `config-persistence-audit.md` — BUG 1: Rust struct missing 5 fields
2. `process-management-audit.md` — BUG 2: No single-instance plugin
3. `keyboard-shortcuts-audit.md` — BUG 3: Shortcut mismatch + BUG 5: voice control regression
4. `ui-ux-audit.md` — All UI/UX issues documented

---

## Phase 1: Critical Backend Fixes

**Branch:** `fix/critical-backend` from `dev`
**Estimated tasks:** 18
**Depends on:** Phase 0 reports

### Task 1.1: Create dev branch

**Files:** None

- [ ] **Step 1: Create and push dev branch**

```bash
git checkout main
git checkout -b dev
git push -u origin dev
```

- [ ] **Step 2: Create feature branch**

```bash
git checkout -b fix/critical-backend
git push -u origin fix/critical-backend
```

---

### Task 1.2: Add missing fields to Rust WhisperConfig

**Files:**
- Modify: `tauri-app/src-tauri/src/commands.rs:40-56`

**Context:** The Rust struct has 16 fields. TypeScript defines 21 (16 + 5 missing). We need to add the 5 missing fields with `#[serde(default)]` for backwards compat with existing env files that don't have these keys.

- [ ] **Step 1: Add VoiceActivationMode, PostProcessingMode, PostProcessingTrigger enums to commands.rs**

Add these enums BEFORE the WhisperConfig struct (around line 35):

```rust
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum VoiceActivationMode {
    Hold,
    Toggle,
}

impl Default for VoiceActivationMode {
    fn default() -> Self {
        Self::Toggle
    }
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PostProcessingMode {
    Off,
    Light,
    Aggressive,
    Agentic,
    Writing,
    Code,
    Structure,
    Persona,
    Clarity,
}

impl Default for PostProcessingMode {
    fn default() -> Self {
        Self::Off
    }
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PostProcessingTrigger {
    Always,
    Manual,
    AutoLong,
    Preview,
}

impl Default for PostProcessingTrigger {
    fn default() -> Self {
        Self::Always
    }
}
```

- [ ] **Step 2: Add 5 missing fields to WhisperConfig struct**

Add these fields at the end of the struct (after `log_level`):

```rust
#[serde(default)]
voice_activation_mode: VoiceActivationMode,
#[serde(default)]
post_processing_enabled: bool,
#[serde(default)]
post_processing_mode: PostProcessingMode,
#[serde(default)]
post_processing_trigger: PostProcessingTrigger,
#[serde(default = "default_indicator_enabled")]
indicator_enabled: bool,
```

Add the default function outside the struct:

```rust
fn default_indicator_enabled() -> bool {
    true
}
```

- [ ] **Step 3: Verify Rust compilation**

Run: `cd tauri-app/src-tauri && cargo check`
Expected: Clean compilation, no errors

- [ ] **Step 4: Commit**

```bash
git add tauri-app/src-tauri/src/commands.rs
git commit -m "fix(config): Add 5 missing fields to Rust WhisperConfig struct

Add voice_activation_mode, post_processing_enabled, post_processing_mode,
post_processing_trigger, and indicator_enabled to match TypeScript types.
Uses #[serde(default)] for backwards compatibility with existing env files."
```

---

### Task 1.3: Update env file read/write for new fields

**Files:**
- Modify: `tauri-app/src-tauri/src/commands.rs` (load_config_from_env_file, save_config_to_env_file)

**Context:** `load_config_from_env_file()` reads env vars line-by-line. `save_config_to_env_file()` writes a HashMap. Both need to handle the 5 new fields.

- [ ] **Step 1: Add new env var reading to load_config_from_env_file()**

Inside the `load_config_from_env_file()` function, after the existing field parsing, add:

```rust
"WHISPER_ACTIVATION_MODE" => {
    config.voice_activation_mode = match value.as_str() {
        "hold" => VoiceActivationMode::Hold,
        _ => VoiceActivationMode::Toggle,
    };
}
"WHISPER_POST_PROCESSING_ENABLED" => {
    config.post_processing_enabled = value == "true" || value == "1";
}
"WHISPER_POST_PROCESSING_MODE" => {
    config.post_processing_mode = match value.as_str() {
        "light" => PostProcessingMode::Light,
        "aggressive" => PostProcessingMode::Aggressive,
        "agentic" => PostProcessingMode::Agentic,
        "writing" => PostProcessingMode::Writing,
        "code" => PostProcessingMode::Code,
        "structure" => PostProcessingMode::Structure,
        "persona" => PostProcessingMode::Persona,
        "clarity" => PostProcessingMode::Clarity,
        _ => PostProcessingMode::Off,
    };
}
"WHISPER_POST_PROCESSING_TRIGGER" => {
    config.post_processing_trigger = match value.as_str() {
        "manual" => PostProcessingTrigger::Manual,
        "auto_long" => PostProcessingTrigger::AutoLong,
        "preview" => PostProcessingTrigger::Preview,
        _ => PostProcessingTrigger::Always,
    };
}
"WHISPER_INDICATOR" => {
    config.indicator_enabled = value == "true" || value == "1";
}
```

- [ ] **Step 2: Add new env var writing to save_config_to_env_file()**

Inside `save_config_to_env_file()`, add entries to the HashMap:

```rust
env_vars.insert("WHISPER_ACTIVATION_MODE".to_string(),
    match &config.voice_activation_mode {
        VoiceActivationMode::Hold => "hold".to_string(),
        VoiceActivationMode::Toggle => "toggle".to_string(),
    });
env_vars.insert("WHISPER_POST_PROCESSING_ENABLED".to_string(),
    config.post_processing_enabled.to_string());
env_vars.insert("WHISPER_POST_PROCESSING_MODE".to_string(),
    match &config.post_processing_mode {
        PostProcessingMode::Off => "off",
        PostProcessingMode::Light => "light",
        PostProcessingMode::Aggressive => "aggressive",
        PostProcessingMode::Agentic => "agentic",
        PostProcessingMode::Writing => "writing",
        PostProcessingMode::Code => "code",
        PostProcessingMode::Structure => "structure",
        PostProcessingMode::Persona => "persona",
        PostProcessingMode::Clarity => "clarity",
    }.to_string());
env_vars.insert("WHISPER_POST_PROCESSING_TRIGGER".to_string(),
    match &config.post_processing_trigger {
        PostProcessingTrigger::Always => "always",
        PostProcessingTrigger::Manual => "manual",
        PostProcessingTrigger::AutoLong => "auto_long",
        PostProcessingTrigger::Preview => "preview",
    }.to_string());
env_vars.insert("WHISPER_INDICATOR".to_string(),
    config.indicator_enabled.to_string());
```

- [ ] **Step 3: Verify compilation**

Run: `cd tauri-app/src-tauri && cargo check`
Expected: Clean

- [ ] **Step 4: Commit**

```bash
git add tauri-app/src-tauri/src/commands.rs
git commit -m "fix(config): Add env file read/write for 5 missing config fields

Map WHISPER_ACTIVATION_MODE, WHISPER_POST_PROCESSING_ENABLED,
WHISPER_POST_PROCESSING_MODE, WHISPER_POST_PROCESSING_TRIGGER,
WHISPER_INDICATOR to/from env file."
```

---

### Task 1.4: Fix default mode to toggle across all layers

**Files:**
- Modify: `tauri-app/src/hooks/useWhisperState.ts` (demoConfig)
- Verify: `src/whisper_hotkey/app.py:247-248` (already defaults to toggle)
- Already done: Rust struct defaults to Toggle (Task 1.2)

- [ ] **Step 1: Update demoConfig in useWhisperState.ts**

Find the `demoConfig` object and change `voice_activation_mode` from `'hold'` to `'toggle'`:

```typescript
// Change this:
voice_activation_mode: 'hold' as VoiceActivationMode,
// To this:
voice_activation_mode: 'toggle' as VoiceActivationMode,
```

- [ ] **Step 2: Verify Python daemon default is toggle**

Check `src/whisper_hotkey/app.py:247-248` — should already be:
```python
add_argument("--activation-mode", default=os.environ.get("WHISPER_ACTIVATION_MODE", "toggle"))
```

If not, update it.

- [ ] **Step 3: Commit**

```bash
git add tauri-app/src/hooks/useWhisperState.ts
git commit -m "fix(config): Default voice activation mode to toggle

Align demoConfig with Rust and Python defaults (toggle, not hold)."
```

---

### Task 1.5: Add single-instance plugin

**Files:**
- Modify: `tauri-app/src-tauri/Cargo.toml`
- Modify: `tauri-app/src-tauri/src/lib.rs`
- Modify: `tauri-app/package.json`

- [ ] **Step 1: Add Rust dependency**

In `Cargo.toml`, add after existing tauri-plugin lines:

```toml
tauri-plugin-single-instance = "2"
```

- [ ] **Step 2: Register plugin in lib.rs**

In `lib.rs`, add to the plugin chain (after existing `.plugin()` calls):

```rust
.plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
    let _ = app
        .get_webview_window("main")
        .expect("no main window")
        .set_focus();
}))
```

Add the import at the top if needed (Tauri 2 plugins auto-import).

- [ ] **Step 3: Add npm dependency**

In `tauri-app/package.json`, add to dependencies:

```json
"@tauri-apps/plugin-single-instance": "2"
```

Then run: `cd tauri-app && npm install`

- [ ] **Step 4: Verify compilation**

Run: `cd tauri-app/src-tauri && cargo check`
Expected: Clean

- [ ] **Step 5: Commit**

```bash
git add tauri-app/src-tauri/Cargo.toml tauri-app/src-tauri/src/lib.rs tauri-app/package.json tauri-app/package-lock.json
git commit -m "fix(process): Add single-instance plugin to prevent duplicate windows

Register tauri-plugin-single-instance to focus existing window instead
of spawning a new one when the app is launched again."
```

---

### Task 1.6: Fix keyboard shortcuts — add Alt+Space for mode cycling

**Files:**
- Modify: `src/whisper_hotkey/app.py` (X11 constants, grab(), event handler)
- Modify: `tauri-app/src/App.tsx` (footer text)

**Context:** Currently Ctrl+Shift+M cycles modes. User wants Ctrl+Shift+Alt+Space. Keep Ctrl+Space for dictation.

- [ ] **Step 1: Add Alt key constants to app.py**

After the existing X11 constants (around line 56), add:

```python
XK_ALT_L = 0xFFE9
XK_ALT_R = 0xFFEA
```

- [ ] **Step 2: Register Ctrl+Shift+Alt+Space key grab in grab() method**

Find the `grab()` method. After the existing Ctrl+Space grabs, add the mode cycling key grab. Register with all modifier variants (numlock, caps, scroll):

```python
# Mode cycling: Ctrl+Shift+Alt+Space
modifiers_with_alt = self.ControlMask | self.ShiftMask | self.Mod1Mask
for extra_mod in [0, self.Mod2Mask, self.LockMask, self.Mod5Mask, 
                  self.Mod2Mask | self.LockMask, self.Mod2Mask | self.Mod5Mask,
                  self.LockMask | self.Mod5Mask, self.Mod2Mask | self.LockMask | self.Mod5Mask]:
    self._grab_key(XK_SPACE, modifiers_with_alt | extra_mod)
```

- [ ] **Step 3: Update event loop handler for mode cycling**

Find the mode cycling handler (around line 1251-1253). Replace the XK_M check with Alt+Space detection:

```python
# OLD: if keycode == XK_M and (event.state & (self.ControlMask | self.ShiftMask)):
# NEW:
if keycode == XK_SPACE and (event.state & (self.ControlMask | self.ShiftMask | self.Mod1Mask)):
    # Cycle mode
    self.cycle_mode()
```

Add `XK_SPACE` import if not already present (it should be, since it's used for dictation).

- [ ] **Step 4: Remove XK_M constant and old mode grab (if any)**

Remove `XK_M = 0x6D` from constants. Remove any old Ctrl+Shift+M grab from `grab()`.

- [ ] **Step 5: Update UI footer in App.tsx**

Find the footer shortcut display (around line 223). Change:

```tsx
// OLD: Ctrl+Shift+S
// NEW:
<span className="text-[10px] text-muted-foreground">
  Ctrl+Shift+Alt+Space — Cycle mode
</span>
```

- [ ] **Step 6: Commit**

```bash
git add src/whisper_hotkey/app.py tauri-app/src/App.tsx
git commit -m "fix(hotkeys): Change mode cycling shortcut to Ctrl+Shift+Alt+Space

Replace Ctrl+Shift+M with Ctrl+Shift+Alt+Space for mode cycling.
Register all X11 modifier variants. Update UI footer to match."
```

---

### Task 1.7: Add X11 debug logging for voice control regression

**Files:**
- Modify: `src/whisper_hotkey/app.py` (grab() method, event loop)

**Context:** Voice control worked from terminal but broke through Tauri. Add logging to diagnose.

- [ ] **Step 1: Add logging to grab() for each key registration**

In the `grab()` method, after each `XGrabKey` call, add:

```python
logger.info(f"Registered hotkey: keycode={keycode}, modifiers={modifiers}")
```

- [ ] **Step 2: Add logging to event loop for key events**

In the event loop, add logging at key points:

```python
# On KeyPress:
logger.debug(f"KeyPress: keycode={event.keycode}, state={event.state}")

# On KeyRelease:
logger.debug(f"KeyRelease: keycode={event.keycode}, state={event.state}")
```

- [ ] **Step 3: Add logging for activation mode on startup**

In the daemon startup, log the active mode:

```python
logger.info(f"Activation mode: {self.activation_mode}")
logger.info(f"Config env file: {os.environ.get('WHISPER_CONFIG_ENV_FILE', 'not set')}")
```

- [ ] **Step 4: Ensure DISPLAY env var is passed to daemon**

In `commands.rs` `start_daemon()`, explicitly pass DISPLAY:

```rust
let child = Command::new("easy-local-whisper-hotkey")
    .arg("run")
    .env("WHISPER_CONFIG_ENV_FILE", env_file)
    .env("DISPLAY", std::env::var("DISPLAY").unwrap_or_else(|_| ":0".to_string()))
    // ... rest of spawn
```

- [ ] **Step 5: Commit**

```bash
git add src/whisper_hotkey/app.py tauri-app/src-tauri/src/commands.rs
git commit -m "fix(debug): Add X11 key grab logging and ensure DISPLAY env var

Add debug logging to key grab registration and event handling.
Pass DISPLAY env var explicitly to daemon subprocess.
Aids diagnosing voice control regression through Tauri."
```

---

### Task 1.8: Verify Phase 1 and merge

- [ ] **Step 1: Full Rust build check**

Run: `cd tauri-app/src-tauri && cargo build`
Expected: Success

- [ ] **Step 2: Verify config round-trip**

Start the Tauri app. Change voice_activation_mode to "hold" in UI. Close and restart. Verify it persists as "hold".

- [ ] **Step 3: Verify single-instance**

Start the Tauri app. Try to launch another instance. Expected: existing window focuses, no duplicate.

- [ ] **Step 4: Verify keyboard shortcut**

Start daemon. Press Ctrl+Shift+Alt+Space. Expected: mode cycles. Press Ctrl+Space. Expected: dictation activates.

- [ ] **Step 5: Merge to dev**

```bash
git checkout dev
git merge fix/critical-backend
git push origin dev
git branch -d fix/critical-backend
git push origin --delete fix/critical-backend
```

---

## Phase 2: Status Page Redesign

**Branch:** `feat/status-page-redesign` from `dev`
**Estimated tasks:** 14

### Task 2.1: Create feature branch

- [ ] **Step 1: Create and push branch**

```bash
git checkout dev
git pull origin dev
git checkout -b feat/status-page-redesign
git push -u origin feat/status-page-redesign
```

---

### Task 2.2: Add per-tab window sizing infrastructure

**Files:**
- Modify: `tauri-app/src-tauri/tauri.conf.json`
- Create: `tauri-app/src/hooks/useWindowResize.ts`
- Modify: `tauri-app/src/App.tsx`

- [ ] **Step 1: Update tauri.conf.json window defaults**

Change initial window size to be more compact:

```json
"windows": [
  {
    "title": "Whisper Hotkey",
    "width": 280,
    "height": 360,
    "minWidth": 260,
    "minHeight": 320,
    "maxWidth": 350,
    "maxHeight": 800,
    "resizable": true,
    "centered": true,
    "decorations": true
  }
]
```

- [ ] **Step 2: Create useWindowResize hook**

Create `tauri-app/src/hooks/useWindowResize.ts`:

```typescript
import { getCurrentWindow } from '@tauri-apps/api/window';
import { PhysicalSize } from '@tauri-apps/api/dpi';

const TAB_SIZES: Record<string, { width: number; height: number }> = {
  status: { width: 280, height: 360 },
  modes: { width: 280, height: 400 },
  config: { width: 280, height: 600 },
};

export async function resizeWindowForTab(tab: string) {
  try {
    const size = TAB_SIZES[tab] || TAB_SIZES.status;
    const appWindow = getCurrentWindow();
    await appWindow.setSize(new PhysicalSize(size.width, size.height));
  } catch (e) {
    // Window API may not be available in dev mode
    console.warn('Window resize failed:', e);
  }
}
```

- [ ] **Step 3: Integrate into App.tsx tab switching**

In the tab change handler, call `resizeWindowForTab()`:

```typescript
import { resizeWindowForTab } from './hooks/useWindowResize';

// In the tab change handler:
const handleTabChange = (tab: string) => {
  setActiveTab(tab);
  resizeWindowForTab(tab);
};
```

- [ ] **Step 4: Commit**

```bash
git add tauri-app/src-tauri/tauri.conf.json tauri-app/src/hooks/useWindowResize.ts tauri-app/src/App.tsx
git commit -m "feat(ui): Add per-tab dynamic window sizing

Each tab (status, modes, config) gets its own window dimensions.
Status: 280x360, Modes: 280x400, Config: 280x600.
Narrower initial size (280px vs 320px)."
```

---

### Task 2.3: Create mini waveform volume visualization

**Files:**
- Create: `tauri-app/src/components/VolumeWaveform.tsx`

- [ ] **Step 1: Create VolumeWaveform component**

```tsx
import React, { useRef, useEffect } from 'react';

interface VolumeWaveformProps {
  volume: number; // 0-1
  isActive: boolean;
}

export function VolumeWaveform({ volume, isActive }: VolumeWaveformProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>(0);
  const timeRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const draw = () => {
      const { width, height } = canvas;
      ctx.clearRect(0, 0, width, height);

      const bars = 24;
      const barWidth = (width - (bars - 1) * 2) / bars;
      const centerY = height / 2;

      for (let i = 0; i < bars; i++) {
        const phase = timeRef.current * 0.05 + i * 0.3;
        const amplitude = isActive
          ? Math.sin(phase) * 0.3 + volume * 0.7
          : 0.05;
        const barHeight = Math.abs(amplitude) * height * 0.8;

        const x = i * (barWidth + 2);
        const y = centerY - barHeight / 2;

        // Gradient from primary teal to secondary purple
        const hue = 159 + (i / bars) * 101; // 159 (teal) → 260 (purple)
        ctx.fillStyle = `hsla(${hue}, 84%, 39%, ${isActive ? 0.8 : 0.2})`;
        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, barHeight, 2);
        ctx.fill();
      }

      timeRef.current++;
      animationRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(animationRef.current);
  }, [volume, isActive]);

  return (
    <canvas
      ref={canvasRef}
      width={240}
      height={48}
      className="w-full h-12"
    />
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add tauri-app/src/components/VolumeWaveform.tsx
git commit -m "feat(ui): Add mini waveform volume visualization component

Canvas-based animated bar graph with teal-to-purple gradient.
Responds to volume level (0-1) and active state."
```

---

### Task 2.4: Add volume event emission to Rust backend

**Files:**
- Modify: `tauri-app/src-tauri/src/commands.rs`
- Modify: `tauri-app/src/hooks/useWhisperState.ts`
- Modify: `tauri-app/src/types/whisper.ts`

- [ ] **Step 1: Add VolumeEvent to TypeScript types**

In `whisper.ts`, add to TauriEvent union:

```typescript
export type TauriEvent = 
  | 'streaming-text'
  | 'daemon-started'
  | 'daemon-stopped'
  | 'volume-level'  // NEW
  | 'recording-state';  // NEW

export interface VolumePayload {
  level: number; // 0.0 - 1.0
}

export interface RecordingStatePayload {
  is_recording: boolean;
  mode: string;
}
```

- [ ] **Step 2: Add volume monitoring to Rust backend**

In `commands.rs`, add a new command that reads daemon stdout for volume events. The Python daemon can emit `VOLUME:0.5` lines on stdout, which the Rust backend parses:

```rust
use std::io::{BufRead, BufReader};
use std::sync::mpsc;

pub fn spawn_stdout_reader(child: &mut Child, app_handle: tauri::AppHandle) {
    let stdout = child.stdout.take().expect("no stdout");
    let reader = BufReader::new(stdout);
    
    std::thread::spawn(move || {
        for line in reader.lines() {
            match line {
                Ok(text) => {
                    if text.starts_with("VOLUME:") {
                        if let Ok(level) = text[7..].parse::<f64>() {
                            let _ = app_handle.emit("volume-level", serde_json::json!({ "level": level }));
                        }
                    } else if text.starts_with("RECORDING:") {
                        let is_recording = text[10..].starts_with("true");
                        let _ = app_handle.emit("recording-state", serde_json::json!({ "is_recording": is_recording }));
                    } else if !text.is_empty() {
                        let _ = app_handle.emit("streaming-text", serde_json::json!({ "text": text }));
                    }
                }
                Err(_) => break,
            }
        }
    });
}
```

Update `start_daemon` to call this after spawning the child.

- [ ] **Step 3: Add volume state to useWhisperState**

In `useWhisperState.ts`, add:

```typescript
const [volumeLevel, setVolumeLevel] = useState(0);
const [isRecording, setIsRecording] = useState(false);

// In the listen setup:
const unlistenVolume = await listen<number>('volume-level', (event) => {
  setVolumeLevel(event.payload.level);
});

const unlistenRecording = await listen<boolean>('recording-state', (event) => {
  setIsRecording(event.payload.is_recording);
});
```

- [ ] **Step 4: Commit**

```bash
git add tauri-app/src-tauri/src/commands.rs tauri-app/src/hooks/useWhisperState.ts tauri-app/src/types/whisper.ts
git commit -m "feat(status): Add volume level and recording state events

Rust backend reads daemon stdout for VOLUME: and RECORDING: events.
Frontend subscribes and exposes volumeLevel and isRecording state."
```

---

### Task 2.5: Add volume emission to Python daemon

**Files:**
- Modify: `src/whisper_hotkey/app.py`

- [ ] **Step 1: Add periodic volume output during recording**

In the recording/audio capture loop, add periodic volume calculation:

```python
import numpy as np

# In the audio capture callback or recording loop:
def emit_volume_level(audio_data: bytes, sample_rate: int = 16000):
    """Calculate RMS volume and emit to stdout."""
    samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
    rms = np.sqrt(np.mean(samples ** 2)) / 32768.0
    level = min(1.0, rms * 3.0)  # Amplify and clamp
    print(f"VOLUME:{level:.3f}", flush=True)
```

Call this periodically (every ~100ms) during recording.

- [ ] **Step 2: Emit recording state**

When recording starts/stops:

```python
print("RECORDING:true", flush=True)  # On start
print("RECORDING:false", flush=True)  # On stop
```

- [ ] **Step 3: Commit**

```bash
git add src/whisper_hotkey/app.py
git commit -m "feat(daemon): Emit volume level and recording state to stdout

Periodic VOLUME:N.NNN output during recording for waveform display.
RECORDING:true/false on record start/stop events."
```

---

### Task 2.6: Redesign Status tab UI

**Files:**
- Modify: `tauri-app/src/App.tsx` (status tab section)

- [ ] **Step 1: Replace status tab content**

Replace the current status display (PID, emoji) with:

```tsx
{/* Status Tab */}
{activeTab === 'status' && (
  <div className="flex flex-col items-center gap-4 p-4">
    {/* Current mode badge */}
    <div className="flex items-center gap-2">
      <span className="text-xs text-muted-foreground">Mode:</span>
      <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-primary/20 text-primary border border-primary/30">
        {config?.voice_activation_mode === 'hold' ? '✋ Hold' : '🔘 Toggle'}
      </span>
    </div>

    {/* Waveform visualization */}
    <VolumeWaveform volume={volumeLevel} isActive={isRecording} />

    {/* Recording indicator */}
    <div className="flex items-center gap-2">
      <span className={`text-2xl ${isRecording ? 'animate-pulse' : ''}`}>
        {isRecording ? '🎙️' : '🔴'}
      </span>
      <span className="text-xs text-muted-foreground">
        {isRecording ? 'Recording...' : (status?.is_running ? 'Listening' : 'Stopped')}
      </span>
    </div>

    {/* Streaming text */}
    <StreamingTextDisplay text={streamText} />

    {/* Controls */}
    <div className="flex gap-2 w-full">
      {!status?.is_running ? (
        <Button onClick={startDaemon} className="flex-1" variant="default" size="sm">
          ▶ Start
        </Button>
      ) : (
        <Button onClick={stopDaemon} className="flex-1" variant="destructive" size="sm">
          ⏹ Stop
        </Button>
      )}
      <Button onClick={refreshStatus} variant="outline" size="sm" title="Refresh daemon status">
        🔄
      </Button>
    </div>
  </div>
)}
```

- [ ] **Step 2: Commit**

```bash
git add tauri-app/src/App.tsx
git commit -m "feat(status): Redesign status tab with waveform and recording indicator

Replace PID display with volume waveform, recording state indicator,
mode badge, and cleaner controls. Add tooltip to refresh button."
```

---

### Task 2.7: Verify Phase 2 and merge

- [ ] **Step 1: Visual check** — Status page shows waveform, mode badge, recording indicator
- [ ] **Step 2: Window sizing** — Switch between tabs, verify window resizes
- [ ] **Step 3: Merge to dev**

```bash
git checkout dev
git merge feat/status-page-redesign
git push origin dev
git branch -d feat/status-page-redesign
git push origin --delete feat/status-page-redesign
```

---

## Phase 3: Config Panel Overhaul

**Branch:** `feat/config-panel-overhaul` from `dev`
**Estimated tasks:** 16

### Task 3.1: Create feature branch

- [ ] Create branch from dev

```bash
git checkout dev && git pull origin dev
git checkout -b feat/config-panel-overhaul
git push -u origin feat/config-panel-overhaul
```

---

### Task 3.2: Add Tauri dialog plugin for file pickers

**Files:**
- Modify: `tauri-app/src-tauri/Cargo.toml`
- Modify: `tauri-app/src-tauri/src/lib.rs`
- Modify: `tauri-app/package.json`
- Modify: `tauri-app/src-tauri/capabilities/default.json`

- [ ] **Step 1: Add plugin dependency**

Cargo.toml:
```toml
tauri-plugin-dialog = "2"
```

package.json:
```json
"@tauri-apps/plugin-dialog": "2"
```

- [ ] **Step 2: Register plugin in lib.rs**

```rust
.plugin(tauri_plugin_dialog::init())
```

- [ ] **Step 3: Add dialog capability**

In `capabilities/default.json`, add to permissions:
```json
"dialog:default",
"dialog:allow-open",
"dialog:allow-save"
```

- [ ] **Step 4: Install npm dep**

```bash
cd tauri-app && npm install
```

- [ ] **Step 5: Verify compilation**

```bash
cd tauri-app/src-tauri && cargo check
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(config): Add tauri-plugin-dialog for file picker support

Register dialog plugin for file path selection in config panel."
```

---

### Task 3.3: Create FilePickerInput component

**Files:**
- Create: `tauri-app/src/components/FilePickerInput.tsx`

- [ ] **Step 1: Create the component**

```tsx
import { open } from '@tauri-apps/plugin-dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';

interface FilePickerInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  label?: string;
}

function toDisplayPath(path: string): string {
  const home = '/home/' + (typeof window !== 'undefined' ? '' : '');
  // We'll use a heuristic: if path starts with /home/USER/, replace with ~/
  return path.replace(/^\/home\/[^/]+\//, '~/');
}

function toAbsolutePath(path: string): string {
  if (path.startsWith('~/')) {
    // This will be resolved server-side; for now store as-is
    return path;
  }
  return path;
}

export function FilePickerInput({ value, onChange, placeholder, label }: FilePickerInputProps) {
  const handlePick = async () => {
    const selected = await open({
      multiple: false,
      directory: false,
    });
    if (selected) {
      onChange(selected as string);
    }
  };

  return (
    <div className="flex items-center gap-1.5">
      <Input
        value={toDisplayPath(value)}
        onChange={(e) => onChange(toAbsolutePath(e.target.value))}
        placeholder={placeholder}
        className="text-xs h-7 flex-1 bg-card border-border"
      />
      <Button
        variant="outline"
        size="sm"
        onClick={handlePick}
        className="h-7 px-2 text-xs shrink-0"
        title={`Browse for ${label || 'file'}`}
      >
        📂
      </Button>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add tauri-app/src/components/FilePickerInput.tsx
git commit -m "feat(config): Add FilePickerInput component with ~/ display

Shows ~/ relative paths in display, stores absolute paths.
File picker button opens native dialog."
```

---

### Task 3.4: Create AudioSourceSelect component

**Files:**
- Create: `tauri-app/src/components/AudioSourceSelect.tsx`

- [ ] **Step 1: Create the component**

```tsx
import { useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';

interface AudioSource {
  id: string;
  name: string;
}

interface AudioSourceSelectProps {
  value: string;
  onChange: (value: string) => void;
}

export function AudioSourceSelect({ value, onChange }: AudioSourceSelectProps) {
  const [sources, setSources] = useState<AudioSource[]>([]);
  const [defaultSource, setDefaultSource] = useState<string>('');

  useEffect(() => {
    loadSources();
  }, []);

  const loadSources = async () => {
    try {
      const list = await invoke<AudioSource[]>('list_sources');
      setSources(list);
      // Auto-select default mic if no value set
      if (!value && list.length > 0) {
        const first = list[0]?.id || '';
        setDefaultSource(first);
        onChange(first);
      }
    } catch (e) {
      console.warn('Failed to load audio sources:', e);
    }
  };

  return (
    <Select value={value || defaultSource} onValueChange={onChange}>
      <SelectTrigger className="h-7 text-xs bg-card border-border">
        <SelectValue placeholder="Select audio source..." />
      </SelectTrigger>
      <SelectContent className="bg-popover border-border backdrop-blur-sm">
        {sources.map((source) => (
          <SelectItem key={source.id} value={source.id} className="text-xs">
            {source.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add tauri-app/src/components/AudioSourceSelect.tsx
git commit -m "feat(config): Add AudioSourceSelect dropdown component

Populated from list_sources command. Auto-selects first available source."
```

---

### Task 3.5: Create PostProcessingGrid component (3x3 mode selector)

**Files:**
- Create: `tauri-app/src/components/PostProcessingGrid.tsx`

- [ ] **Step 1: Create the component**

```tsx
import { PostProcessingMode } from '../types/whisper';

const MODES: { value: PostProcessingMode; label: string; icon: string }[] = [
  { value: 'off', label: 'Off', icon: '⊘' },
  { value: 'light', label: 'Light', icon: '✨' },
  { value: 'aggressive', label: 'Aggressive', icon: '⚡' },
  { value: 'agentic', label: 'Agentic', icon: '🤖' },
  { value: 'writing', label: 'Writing', icon: '✏️' },
  { value: 'code', label: 'Code', icon: '💻' },
  { value: 'structure', label: 'Structure', icon: '📐' },
  { value: 'persona', label: 'Persona', icon: '🎭' },
  { value: 'clarity', label: 'Clarity', icon: '🔍' },
];

interface PostProcessingGridProps {
  value: PostProcessingMode;
  onChange: (value: PostProcessingMode) => void;
}

export function PostProcessingGrid({ value, onChange }: PostProcessingGridProps) {
  return (
    <div className="grid grid-cols-3 gap-1.5">
      {MODES.map((mode) => (
        <button
          key={mode.value}
          onClick={() => onChange(mode.value)}
          className={`
            flex flex-col items-center gap-0.5 p-2 rounded-md text-xs transition-all
            ${value === mode.value
              ? 'border-2 border-primary bg-primary/10 ring-1 ring-primary/30 shadow-sm shadow-primary/20'
              : 'border border-border bg-card hover:bg-card/80 hover:border-border/80'
            }
          `}
        >
          <span className="text-base">{mode.icon}</span>
          <span className="text-[10px]">{mode.label}</span>
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add tauri-app/src/components/PostProcessingGrid.tsx
git commit -m "feat(config): Add 3x3 post-processing mode grid selector

Replace dropdown with compact grid. Primary border + ring for active state."
```

---

### Task 3.6: Create RulesManager component (suppress regex redesign)

**Files:**
- Create: `tauri-app/src/components/RulesManager.tsx`
- Modify: `tauri-app/src/types/whisper.ts` (add Rule types)

- [ ] **Step 1: Add Rule types to whisper.ts**

```typescript
export interface FilterRule {
  id: string;
  name: string;
  pattern: string;
  enabled: boolean;
  is_builtin: boolean;
}

// Update WhisperConfig to use rules instead of single suppress_regex:
// suppress_regex: string → suppress_rules: FilterRule[]
```

**Note:** This is a significant schema change. For Phase 3, we'll store rules as a JSON string in the existing `suppress_regex` field for backwards compat. The Rust backend can parse it. A future phase can migrate to a dedicated field.

- [ ] **Step 2: Create RulesManager component**

```tsx
import { useState } from 'react';
import { FilterRule } from '../types/whisper';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Switch } from './ui/switch';

const DEFAULT_RULES: FilterRule[] = [
  { id: 'builtin-1', name: 'Remove filler words', pattern: '\\b(um|uh|ah|er|hmm)\\b[,.]?\\s*', enabled: true, is_builtin: true },
  { id: 'builtin-2', name: 'Remove repeated words', pattern: '\\b(\\w+)\\s+\\1\\b', enabled: false, is_builtin: true },
  { id: 'builtin-3', name: 'Clean timestamps', pattern: '\\d{1,2}:\\d{2}(?::\\d{2})?', enabled: false, is_builtin: true },
];

interface RulesManagerProps {
  rulesJson: string;  // JSON string from suppress_regex field
  onChange: (json: string) => void;
}

function parseRules(json: string): FilterRule[] {
  try {
    const parsed = JSON.parse(json);
    if (Array.isArray(parsed)) return parsed;
  } catch {}
  // Legacy: treat as single regex pattern
  if (json.trim()) {
    return [{ id: 'legacy', name: 'Custom pattern', pattern: json, enabled: true, is_builtin: false }];
  }
  return [...DEFAULT_RULES];
}

export function RulesManager({ rulesJson, onChange }: RulesManagerProps) {
  const [rules, setRules] = useState<FilterRule[]>(() => parseRules(rulesJson));
  const [newName, setNewName] = useState('');
  const [newPattern, setNewPattern] = useState('');

  const updateRules = (updated: FilterRule[]) => {
    setRules(updated);
    onChange(JSON.stringify(updated));
  };

  const toggleRule = (id: string) => {
    updateRules(rules.map(r => r.id === id ? { ...r, enabled: !r.enabled } : r));
  };

  const removeRule = (id: string) => {
    updateRules(rules.filter(r => r.id !== id));
  };

  const addRule = () => {
    if (!newName || !newPattern) return;
    const rule: FilterRule = {
      id: `custom-${Date.now()}`,
      name: newName,
      pattern: newPattern,
      enabled: true,
      is_builtin: false,
    };
    updateRules([...rules, rule]);
    setNewName('');
    setNewPattern('');
  };

  return (
    <div className="space-y-2">
      {rules.map((rule) => (
        <div key={rule.id} className="flex items-center gap-2 p-2 rounded-md bg-card border border-border">
          <Switch
            checked={rule.enabled}
            onCheckedChange={() => toggleRule(rule.id)}
            className="scale-75"
          />
          <div className="flex-1 min-w-0">
            <div className="text-xs font-medium truncate">{rule.name}</div>
            <div className="text-[10px] text-muted-foreground font-mono truncate">{rule.pattern}</div>
          </div>
          {!rule.is_builtin && (
            <Button variant="ghost" size="sm" onClick={() => removeRule(rule.id)} className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive">
              ✕
            </Button>
          )}
        </div>
      ))}
      
      {/* Add new rule */}
      <div className="flex gap-1.5 p-2 rounded-md border border-dashed border-border">
        <Input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="Rule name"
          className="h-6 text-xs flex-1"
        />
        <Input
          value={newPattern}
          onChange={(e) => setNewPattern(e.target.value)}
          placeholder="Regex pattern"
          className="h-6 text-xs flex-1 font-mono"
        />
        <Button variant="outline" size="sm" onClick={addRule} className="h-6 px-2 text-xs shrink-0">
          + Add
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add tauri-app/src/components/RulesManager.tsx tauri-app/src/types/whisper.ts
git commit -m "feat(config): Add RulesManager component for regex filter rules

Replace single suppress_regex text input with named, togglable rules.
Ships with 3 built-in defaults. Supports custom rules.
Stores as JSON in existing suppress_regex field for backwards compat."
```

---

### Task 3.7: Overhaul ConfigurationPanel with new components

**Files:**
- Modify: `tauri-app/src/components/ConfigurationPanel.tsx`

- [ ] **Step 1: Replace file path inputs with FilePickerInput**

Find all `<TextInput>` or `<input>` used for paths (whisper_cli, log_file) and replace:

```tsx
<FilePickerInput
  value={config.log_file || ''}
  onChange={(v) => updateConfig({ log_file: v })}
  placeholder="~/.config/whisper-hotkey/whisper-hotkey.log"
  label="log file"
/>
```

- [ ] **Step 2: Replace audio source input with AudioSourceSelect**

```tsx
<AudioSourceSelect
  value={config.source || ''}
  onChange={(v) => updateConfig({ source: v })}
/>
```

- [ ] **Step 3: Replace post-processing mode dropdowns with PostProcessingGrid**

```tsx
<PostProcessingGrid
  value={config.post_processing_mode || 'off'}
  onChange={(v) => updateConfig({ post_processing_mode: v })}
/>
```

- [ ] **Step 4: Replace suppress_regex text input with RulesManager**

```tsx
<RulesManager
  rulesJson={config.suppress_regex || ''}
  onChange={(v) => updateConfig({ suppress_regex: v })}
/>
```

- [ ] **Step 5: Increase Switch size and add right padding**

Find all `<Switch>` components. Add size classes:

```tsx
<Switch
  checked={...}
  onCheckedChange={...}
  className="h-5 w-9"  // Bigger than default
/>
```

Add `pr-3` to each feature row container.

- [ ] **Step 6: Update section headers to use smaller text**

Change section header text size from `text-sm` to `text-xs` and add more padding.

- [ ] **Step 7: Commit**

```bash
git add tauri-app/src/components/ConfigurationPanel.tsx
git commit -m "feat(config): Overhaul configuration panel with new components

Replace text inputs with file pickers, audio source dropdown,
3x3 post-processing grid, and rules manager. Increase switch size
and add right padding for scrollbar clearance."
```

---

### Task 3.8: Verify Phase 3 and merge

- [ ] **Step 1: Visual check** — Config panel shows new components, file pickers work
- [ ] **Step 2: Audio source dropdown** — Populates from `list_sources`, auto-selects default
- [ ] **Step 3: Rules manager** — Can add/remove/toggle rules, persists to env file
- [ ] **Step 4: Merge to dev**

```bash
git checkout dev
git merge feat/config-panel-overhaul
git push origin dev
git branch -d feat/config-panel-overhaul
git push origin --delete feat/config-panel-overhaul
```

---

## Phase 4: Modes Tab Polish

**Branch:** `feat/modes-tab-polish` from `dev`
**Estimated tasks:** 6

### Task 4.1: Create feature branch

- [ ] Create branch from dev

```bash
git checkout dev && git pull origin dev
git checkout -b feat/modes-tab-polish
git push -u origin feat/modes-tab-polish
```

---

### Task 4.2: Update ModeQuickSelect active state styling

**Files:**
- Modify: `tauri-app/src/components/ModeQuickSelect.tsx`

- [ ] **Step 1: Change active button to outline + ring + shadow**

Find the active button className and change from solid variant to outline with glow:

```tsx
const buttonClass = isActive
  ? 'border-2 border-primary bg-transparent ring-2 ring-primary/30 shadow-md shadow-primary/20 text-primary'
  : 'border border-border bg-card hover:bg-card/80 text-foreground';
```

- [ ] **Step 2: Add mode descriptions**

Add subtitle text under each mode label:

```tsx
const MODE_DESCRIPTIONS: Record<string, string> = {
  'off': 'No processing',
  'light': 'Punctuation only',
  'aggressive': 'Full grammar fix',
  'agentic': 'AI-powered rewrite',
  'writing': 'Prose optimization',
  'code': 'Code formatting',
  'structure': 'Text restructuring',
  'persona': 'Tone adjustment',
  'clarity': 'Readability boost',
};
```

Show description as small text below mode name:

```tsx
<span className="text-[10px] text-muted-foreground">{MODE_DESCRIPTIONS[mode]}</span>
```

- [ ] **Step 3: Commit**

```bash
git add tauri-app/src/components/ModeQuickSelect.tsx
git commit -m "feat(modes): Polish mode selector with outline active state and descriptions

Active mode uses primary border + ring + shadow glow instead of solid fill.
Add mode descriptions as subtitles below each button."
```

---

### Task 4.3: Verify Phase 4 and merge

- [ ] **Step 1: Visual check** — Active mode has subtle glow, descriptions visible
- [ ] **Step 2: Merge to dev**

```bash
git checkout dev
git merge feat/modes-tab-polish
git push origin dev
git branch -d feat/modes-tab-polish
git push origin --delete feat/modes-tab-polish
```

---

## Phase 5: Global Styling Modernization

**Branch:** `feat/global-styling` from `dev`
**Estimated tasks:** 10

### Task 5.1: Create feature branch

- [ ] Create branch from dev

```bash
git checkout dev && git pull origin dev
git checkout -b feat/global-styling
git push -u origin feat/global-styling
```

---

### Task 5.2: Fix global padding and scrollbar overlap

**Files:**
- Modify: `tauri-app/src/index.css`
- Modify: `tauri-app/src/App.tsx`

- [ ] **Step 1: Add global scrollbar-safe padding**

In `index.css`:

```css
/* Scrollbar-safe padding */
.scroll-container {
  padding-right: 12px;
  scrollbar-width: thin;
  scrollbar-color: hsl(250 20% 12%) transparent;
}

.scroll-container::-webkit-scrollbar {
  width: 4px;
}

.scroll-container::-webkit-scrollbar-track {
  background: transparent;
}

.scroll-container::-webkit-scrollbar-thumb {
  background: hsl(250 20% 20%);
  border-radius: 2px;
}
```

- [ ] **Step 2: Apply scroll-container class to tab content areas in App.tsx**

Add `scroll-container` class to the scrollable divs wrapping each tab's content.

- [ ] **Step 3: Commit**

```bash
git add tauri-app/src/index.css tauri-app/src/App.tsx
git commit -m "style: Add scrollbar-safe padding and thin custom scrollbar

4px thin scrollbar with dark theme colors. 12px right padding prevents
component overlap with scrollbar."
```

---

### Task 5.3: Modernize button styling

**Files:**
- Modify: `tauri-app/src/components/ui/button.tsx`

- [ ] **Step 1: Update button variants**

Make buttons more compact and modern:

```tsx
// Add/modify variants:
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-xs font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground shadow-sm hover:bg-primary/90 active:scale-[0.98]",
        destructive: "bg-red-600 text-white shadow-sm hover:bg-red-700 active:scale-[0.98]",
        outline: "border border-border bg-transparent hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary/20 text-secondary border border-secondary/30 hover:bg-secondary/30",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-8 px-3 py-1.5",
        sm: "h-7 rounded-md px-2.5 text-[11px]",
        lg: "h-10 rounded-md px-6",
        icon: "h-7 w-7",
      },
    },
  }
);
```

- [ ] **Step 2: Commit**

```bash
git add tauri-app/src/components/ui/button.tsx
git commit -m "style: Modernize button variants with compact sizing

Smaller default height, active scale animation, better hover states.
Add secondary variant with transparent bg + colored border."
```

---

### Task 5.4: Fix dropdown/select transparency

**Files:**
- Modify: `tauri-app/src/components/ui/select.tsx`

- [ ] **Step 1: Make SelectContent opaque with blur**

```tsx
// In SelectContent:
const SelectContent = React.forwardRef<...>(
  ({ className, children, position = "popper", ...props }, ref) => (
    <SelectPortal>
      <SelectPrimitive.Content
        ref={ref}
        className={cn(
          "relative z-50 max-h-64 min-w-[8rem] overflow-hidden rounded-md",
          "bg-popover/95 backdrop-blur-md border border-border",
          "text-popover-foreground shadow-lg shadow-black/20",
          "data-[state=open]:animate-in data-[state=closed]:animate-out",
          "data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
          "data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95",
          position === "popper" && "data-[side=bottom]:translate-y-1 data-[side=left]:-translate-x-1 data-[side=right]:translate-x-1 data-[side=top]:-translate-y-1",
          className
        )}
        position={position}
        {...props}
      >
        <SelectPrimitive.Viewport className={cn(
          "p-1",
          position === "popper" && "h-[var(--radix-select-trigger-height)] w-full min-w-[var(--radix-select-trigger-width)]"
        )}>
          {children}
        </SelectPrimitive.Viewport>
      </SelectPrimitive.Content>
    </SelectPortal>
  )
);
```

- [ ] **Step 2: Make SelectItem more compact**

```tsx
const SelectItem = React.forwardRef<...>(
  ({ className, children, ...props }, ref) => (
    <SelectPrimitive.Item
      ref={ref}
      className={cn(
        "relative flex w-full cursor-default select-none items-center rounded-sm py-1 pl-2 pr-6 text-xs",
        "outline-none focus:bg-accent focus:text-accent-foreground",
        "data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
        className
      )}
      {...props}
    >
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
      <SelectPrimitive.ItemIndicator className="absolute right-1 flex h-3 w-3 items-center justify-center">
        <Check className="h-3 w-3" />
      </SelectPrimitive.ItemIndicator>
    </SelectPrimitive.Item>
  )
);
```

- [ ] **Step 3: Commit**

```bash
git add tauri-app/src/components/ui/select.tsx
git commit -m "style: Fix select dropdown with opaque bg, blur, and compact items

bg-popover/95 with backdrop-blur-md. Smaller item height.
Better shadow for depth."
```

---

### Task 5.5: Add depth and polish to card/container styling

**Files:**
- Modify: `tauri-app/src/components/ui/card.tsx`
- Modify: `tauri-app/src/theme/designTokens.ts`

- [ ] **Step 1: Update card with subtle border and shadow**

```tsx
const cardVariants = cva(
  "rounded-lg border border-border/50 bg-card text-card-foreground shadow-sm shadow-black/10",
  ...
);
```

- [ ] **Step 2: Add transition tokens to designTokens.ts**

```typescript
export const transitions = {
  fast: 'transition-all duration-150 ease-in-out',
  normal: 'transition-all duration-200 ease-in-out',
  smooth: 'transition-all duration-300 ease-in-out',
} as const;

export const spacing = {
  section: 'p-3 pr-4',  // Extra right padding for scrollbar
  compact: 'p-2 pr-3',
  relaxed: 'p-4 pr-5',
} as const;
```

- [ ] **Step 3: Commit**

```bash
git add tauri-app/src/components/ui/card.tsx tauri-app/src/theme/designTokens.ts
git commit -m "style: Add card depth and spacing/transition design tokens

Subtle border + shadow on cards. Transition presets for animations.
Section spacing with right padding for scrollbar clearance."
```

---

### Task 5.6: Final global pass — hover states, focus rings, transitions

**Files:**
- Modify: `tauri-app/src/index.css`

- [ ] **Step 1: Add global interaction polish**

```css
/* Better hover states */
button, [role="button"] {
  transition: all 150ms ease-in-out;
}

button:active:not(:disabled) {
  transform: scale(0.98);
}

/* Focus rings */
:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--primary) / 0.3);
}

/* Smooth tab content transitions */
.tab-content {
  animation: fadeIn 150ms ease-in-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Smooth window resize transition */
html, body, #root {
  transition: height 200ms ease-in-out;
}
```

- [ ] **Step 2: Commit**

```bash
git add tauri-app/src/index.css
git commit -m "style: Add global interaction polish — hover, focus, transitions

Active scale on buttons, primary focus rings, tab fade-in animation.
Smooth window resize transition."
```

---

### Task 5.7: Verify Phase 5 and merge

- [ ] **Step 1: Visual check** — All pages look modern, no scrollbar overlap, dropdowns opaque
- [ ] **Step 2: Interaction check** — Buttons have hover/active states, focus rings work
- [ ] **Step 3: Merge to dev**

```bash
git checkout dev
git merge feat/global-styling
git push origin dev
git branch -d feat/global-styling
git push origin --delete feat/global-styling
```

---

## Final: Merge dev → main

After ALL phases are verified on `dev`:

- [ ] **Step 1: Final verification on dev**

Run full test suite, manual smoke test of all features.

- [ ] **Step 2: Merge to main**

```bash
git checkout main
git merge dev
git push origin main
```

- [ ] **Step 3: Verify only main and dev remain**

```bash
git branch -a
# Should show: main, dev (and their remotes)
```

If any feature branches remain:
```bash
git branch -D <branch>
git push origin --delete <branch>
```

---

## Summary of Deliverables

| Phase | Branch | Key Changes | Tasks |
|-------|--------|-------------|-------|
| 0 | N/A | 4 audit reports in docs/reports/critical-reviews/ | N/A |
| 1 | fix/critical-backend | Fix 5 bugs: config fields, single-instance, shortcuts, defaults, logging | 8 |
| 2 | feat/status-page-redesign | Waveform, recording indicator, per-tab sizing | 7 |
| 3 | feat/config-panel-overhaul | File pickers, audio dropdown, PP grid, rules manager | 8 |
| 4 | feat/modes-tab-polish | Outline active state, mode descriptions | 3 |
| 5 | feat/global-styling | Scrollbar fix, button modernization, dropdown fix, polish | 7 |

**Total estimated tasks:** ~33 (across 5 phases)

---

## Dependencies Between Phases

```
Phase 0 (reports) → Phase 1 (backend fixes) → Phase 2 (status)
                                               → Phase 3 (config)
                                               → Phase 4 (modes)
                                               → Phase 5 (styling)
```

Phases 2-5 are independent of each other and can be done in any order after Phase 1. Phase 5 (styling) should ideally be last since it touches global CSS that other phases might override.

---

## Testing Strategy

- **Phase 1:** Rust `cargo check`, manual config persistence test, single-instance test, hotkey test
- **Phase 2:** Visual verification of waveform, window sizing measurement
- **Phase 3:** File picker dialog test, audio source dropdown test, rules CRUD test
- **Phase 4:** Visual verification of mode selector
- **Phase 5:** Visual verification of all pages, interaction polish

Each phase has a manual confirmation checkpoint before merge to `dev`.
