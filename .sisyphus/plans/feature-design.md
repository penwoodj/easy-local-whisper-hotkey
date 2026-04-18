# Feature Design: Grammar Post-Processing + Modes

## Requirements Summary

### Core Features
1. **Gradient ball-of-light indicator** — not flat white circle
2. **Grammar post-processing** — multiple modes, configurable trigger
3. **Auto-off on focus change** — when clicking out of input
4. **Additional text fixer modes** — 3+ creative modes for agentic workflows
5. **Unit tests** — core logic + desktop app
6. **UI component library** — Tauri desktop app polish
7. **Default config** — post-processing OFF by default

### User Context
- Uses voice for **agentic instruction writing** and **brainstorming**
- Primary communication: **Discord** (messaging)
- NOT for coding (yet)
- Wants **multiple trigger modes** (always, manual, auto-long, preview)
- Default: **post-processing disabled**

---

## Proposed Approaches

### Approach A: Modular Incremental (RECOMMENDED)
- **Indicator upgrade** as isolated PR
- **Post-processing system** as independent module with mode selector
- **Auto-off detection** as separate X11 event handler
- **UI** layered: settings → mode toggle → indicator

**Pros:**
- Each feature tested independently
- Easier to disable/enable individually
- Clear PR boundaries

**Cons:**
- More initial setup work
- Requires careful integration testing

---

### Approach B: Monolith Integration
- Add everything to `app.py` in one big PR
- UI manages all settings in single config file

**Pros:**
- Faster to ship (fewer PRs)
- Simpler state management

**Cons:**
- Harder to test edge cases
- Risk of breaking unrelated features
- Difficult to disable individual features

---

### Approach C: Feature Flags + Phased Rollout
- Build behind feature flags in config
- Release incrementally: gradient → post-processing → auto-off → modes

**Pros:**
- Can rollback if issues
- Users can opt-in early

**Cons:**
- More complex deployment
- Config surface gets messy

---

## Recommendation: **Approach A (Modular Incremental)**

**Reasoning:**
1. You want to test different modes independently
2. Each feature has clear failure modes
3. UI can evolve layer-by-layer
4. Matches existing modular structure (Recorder, Transcriber, Daemon as separate)

---

## Design Section 1: Gradient Indicator

### Current State
- `indicator.py`: XRenderFillRectangle with solid colors
- Flat white circle (center) + white-blue outer
- Pulse animation: alpha changes, colors fixed

### Proposed Solution

**Option 1: Pre-generated PNG sprites**
- Generate 32 PNG frames (gradient variations) at install time
- Load frame based on pulse phase in `tick()`
- Use XRender to blit PNG overlay

**Pros:** Fastest runtime, pre-tested visual
**Cons:** No runtime customization, larger install size

**Option 2: Cairo radial gradient (RECOMMENDED)**
- Use `pycairo` to render radial gradient at runtime
- Center: white → outer: transparent blue
- Update every tick with pulse on alpha

**Pros:** Dynamic, customizable, smaller code
**Cons:** Requires pycairo dependency

**Option 3: PIL + PNG buffer**
- Use Pillow to create gradient on-the-fly
- Convert to PNG bytes, load via XCB or XRender

**Pros:** No extra C deps, Python-only
**Cons:** Slower than Cairo

### Recommended: **Option 2 (Cairo radial gradient)**

**Implementation Sketch:**
```python
# indicator.py additions
def _draw_gradient_circle(self, pulse_alpha):
    if not self._ext_render or not self._libxrender or not self._argb_visual:
        return

    # Radial gradient: center bright, outer transparent
    center_color = (1.0, 1.0, 1.0, pulse_alpha * 0.8)  # RGBA
    outer_color = (0.1, 0.2, 0.3, 0.0)  # Transparent blue

    # Use XRender or Cairo to draw radial
    # Or generate PNG via pycairo each tick (cache 32 frames)
```

---

## Design Section 2: Post-Processing Modes

### Planned Modes (6 total)
1. **Off** — no correction (default)
2. **Light** — FullStop punctuation only
3. **Aggressive** — FullStop + Qwen grammar
4. **Agentic** — 2-3 cycle LLM expansion
5. **Writing** — Style/polish focused
6. **Code** — Syntax-aware (for future coding use)

### Proposed Additional Modes (3 more)
7. **Structure** — Bullet/number formatting for brainstormed ideas
8. **Persona** — Tone matching (professional, casual, technical)
9. **Clarity** — Readability scoring + suggestion

### Mode Descriptions

#### Off
- **Action:** Skip all correction
- **Speed:** 0ms
- **Use case:** Quick notes, raw dictation

#### Light
- **Action:** Add punctuation only via FullStop model
- **Speed:** ~1s for 200 words
- **Use case:** Quick readability, minimal changes

#### Aggressive
- **Action:** Grammar + punctuation via Qwen2.5-0.5B
- **Speed:** ~2-3s for 200 words
- **Use case:** Important messages needing full polish

#### Agentic (NEW)
- **Action:** 2-3 cycle LLM expansion of instructions
- **Speed:** ~4-6s (multi-cycle)
- **Use case:** Complex multi-step tasks, detailed prompts
- **Prompt:** "Expand this into a detailed, step-by-step agentic instruction with examples and edge cases covered"

#### Writing (NEW)
- **Action:** Style polish + flow improvement
- **Speed:** ~3-4s
- **Use case:** Prose, documentation, emails
- **Prompt:** "Improve flow, clarity, and tone without changing meaning"

#### Code (for future)
- **Action:** Syntax-aware corrections only
- **Speed:** ~2-3s
- **Use case:** When you use voice for coding

#### Structure (NEW)
- **Action:** Format as bullet points or numbered lists
- **Speed:** ~1-2s
- **Use case:** Brainstorming, idea organization
- **Prompt:** "Format as bulleted list, maintain hierarchy"

#### Persona (NEW)
- **Action:** Match tone (professional/casual/technical)
- **Speed:** ~2-3s
- **Use case:** Discord messaging, audience adaptation
- **Prompt:** "Rewrite in professional tone" / "casual tone" / "technical tone"

#### Clarity (NEW)
- **Action:** Score readability, suggest improvements
- **Speed:** ~1-2s
- **Use case:** Refining complex instructions
- **Prompt:** "Score readability (1-10), suggest improvements"

### Trigger Modes

1. **Always** — Run after every toggle-off
2. **Manual** — UI button to trigger correction
3. **Auto-Long** — Only if >100 words in session
4. **Preview** — Show corrected text, don't replace

### Config Structure

```toml
[postprocessing]
enabled = false  # Default OFF
mode = "light"  # off | light | aggressive | agentic | writing | structure | persona | clarity
trigger = "always"  # always | manual | auto-long | preview
agentic_cycles = 2
```

---

## Design Section 3: Auto-Off on Focus Change

### Current State
- No focus detection
- Manual toggle-off via Ctrl+Space only

### Proposed Solution

**X11 Focus Events:**
- Listen for `FocusOut` events on root window
- When focus lost AND recording active → toggle-off
- Add config option: `auto_off_on_focus = false`

**Implementation:**
```python
# X11HotkeyDaemon additions
def _setup_focus_events(self):
    self.libx11.XSelectInput.argtypes = [...]
    # Register for FocusOut events on root window

def handle_focus_out(self, event):
    if self.recording_active:
        self.logger.log("Focus lost, auto-toggling off")
        self.handle_toggle_session()
```

**Alternative:** XCB focus tracking (more modern X11 API)

---

## Design Section 4: UI Component Library

### Technology Stack
- **Frontend:** React + TypeScript + Tailwind
- **Components:** shadcn/ui primitives
- **Backend:** Tauri 2.x (Rust)
- **State:** Zustand or React Context

### Component Library Structure

```
src/components/
├── settings/
│   ├── SettingsPanel.tsx      # Main settings dialog
│   ├── ModelSelector.tsx         # Whisper model picker
│   ├── ModeSelector.tsx          # Post-processing mode toggle
│   └── TriggerSelector.tsx       # Auto-off trigger config
├── status/
│   ├── RecordingIndicator.tsx   # Recording state visual
│   └── TextCounter.tsx           # Words typed counter
└── ui/
    ├── Button.tsx                 # Reusable button
    ├── Toggle.tsx                 # Switch component
    └── Card.tsx                  # Content container
```

### Tauri IPC Commands

```rust
// src-tauri/commands.rs
#[tauri::command]
async fn set_config(key: String, value: String) -> Result<(), String>

#[tauri::command]
async fn get_config() -> Result<Config, String>

#[tauri::command]
async fn set_postprocess_mode(mode: String) -> Result<(), String>
```

---

## Next Steps

1. **Confirm design direction** — Does this structure match your vision?
2. **Detail any missing modes** — Are there specific text fixer ideas you want?
3. **Prioritize features** — What should we build first?
