# UI/UX Audit Report

**Application:** Easy Local Whisper Hotkey  
**Platform:** Tauri 2.x Desktop App (Linux)  
**Audit Date:** April 18, 2026  
**Current Version:** 0.1.0

---

## Executive Summary

| Severity | Issue Category       | Count | User Impact                                 |
| -------- | -------------------- | ----- | ------------------------------------------- |
| **Critical** | Window Sizing        | 3     | Wasted space, poor UX, accessibility issues |
| **Critical** | Config Tab Usability | 5     | Core features broken, poor discoverability  |
| **High**     | Component Library    | 6     | UI feels dated, accessibility problems      |
| **High**     | Status Page          | 5     | Missing essential visual feedback           |
| **Medium**   | Modes Tab            | 2     | Visual polish, discoverability              |
| **Low**      | Design Polish        | 3     | Nice-to-have refinements                    |

**Total Issues:** 24

**Top Priority Fix Order:**
1. Window dynamic sizing (affects all pages)
2. Config tab file picker + audio source dropdown
3. Component padding + scrollbar overlap
4. Status page waveform + recording indicator
5. Suppress regex → rules manager

---

## Per-Page Analysis

### Status Tab

**Current State:**

The Status tab displays a large emoji (🎙️/🔴) with breathing animation, a status dot with "Idle/Listening" text, and a card showing PID and streaming text. Below are Start/Stop buttons and a reload button.

```
┌────────────────────────┐
│                      │
│       🎙️            │  ← Large animated emoji
│                      │
│    ● Idle            │  ← Status indicator
│                      │
│  ┌────────────────┐  │
│  │ PID: 12345     │  │  ← PID display (not useful)
│  │               │  │
│  │ Hold Ctrl+Space│  │  ← Streaming text
│  │ to start...    │  │
│  │               │  │
│  │ [Start] [↻]  │  │  ← Actions
│  └────────────────┘  │
│                      │
└────────────────────────┘
```

**Issues Found:**

| Severity | Issue                          | Description                                                                      |
| -------- | ------------------------------ | -------------------------------------------------------------------------------- |
| High     | Static PID display             | Shows process ID instead of live data. User doesn't care about PID.              |
| High     | No volume visualization        | No visual feedback for voice input level. Can't tell if mic is working.          |
| High     | Mode not shown                 | Current voice activation mode (toggle/hold) only shown in footer, not main view. |
| High     | No recording indicator         | Shows "Listening" when daemon starts, not when actually recording.               |
| Medium   | Reload button appears disabled | Always has outline variant (not primary), user thinks it's disabled. No tooltip. |
| Low      | Cursor emoji not shown         | Footer mentions "cursor indicator" but emoji only shows externally.              |

**Proposed Redesign:**

```
┌────────────────────────┐
│                      │
│    🎙️  TOGGLE        │  ← Current mode shown above emoji
│                      │
│    ● Listening...     │  ← Active recording state
│                      │
│ ▁▃▅▇█▇▅▃▁▃▅▇█     │  ← Mini waveform (animated)
│                      │
│  ┌────────────────┐  │
│  │ "This is a    │  │
│  │  live test..." │  │  ← Streaming text
│  │               │  │
│  │ [Stop] [↻]   │  │  ← Actions (reload shows tooltip)
│  └────────────────┘  │
│                      │
│  [📍]               │  ← Cursor indicator emoji in-app
└────────────────────────┘
```

**Component-by-Component Breakdown:**

1. **Mode Badge** (NEW)
   - **Before:** None (mode hidden in footer)
   - **After:** Small pill badge above emoji showing "TOGGLE" or "HOLD"
   - **Rationale:** User needs to see current mode at glance without navigating

2. **Large Status Emoji** (KEEP)
   - **Before:** Animated 🎙️ (idle) / 🔴 (running)
   - **After:** Same animation, but add subtle pulse ring when actively recording
   - **Rationale:** User likes this. Enhance rather than replace.

3. **Recording Indicator** (MODIFY)
   - **Before:** "Idle" when daemon off, "Listening" when daemon on
   - **After:** "Idle" → "Listening" (daemon on) → "Recording" (Ctrl+Space pressed)
   - **Rationale:** Three distinct states prevent confusion. User thinks "Listening" means recording, but it doesn't.

4. **Waveform Visualizer** (NEW)
   - **Before:** None
   - **After:** 12-bar mini waveform, animated in real-time from audio volume
   - **Implementation:** Canvas-based, smooth 60fps animation, teal color for active
   - **Rationale:** Critical feedback that mic is working and picking up sound

5. **Streaming Text Card** (KEEP, REPOSITION)
   - **Before:** Full-width card below emoji
   - **After:** Same, but move reload button tooltip: "Refresh status"
   - **Rationale:** Current implementation is good, just needs tooltip.

6. **Cursor Indicator** (ADD)
   - **Before:** Only shown externally in X11 cursor
   - **After:** Small pill at bottom showing [📍] with opacity indicating state
   - **Rationale:** User wants to see in-app confirmation that indicator is working.

---

### Modes Tab

**Current State:**

The Modes tab displays a 3×3 grid of mode buttons (Off, Light, Aggressive, Agentic, Writing, Code, Structure, Persona, Clarity). Active mode uses solid primary color background. Shows "Current: [mode]" pill below grid.

```
┌────────────────────────┐
│                      │
│ ┌───┬───┬───┐      │
│ │🎙️│✨ │🔥 │      │  ← Active = solid teal background
│ ├───┼───┼───┤      │     (too heavy, looks like alert)
│ │🤖│✍️│💻 │      │
│ ├───┼───┼───┤      │
│ │🏗️│👤│💎 │      │
│ └───┴───┴───┘      │
│                      │
│ ┌────────────────┐    │
│ │ Current: Code│    │  ← Status pill
│ └────────────────┘    │
└────────────────────────┘
```

**Issues Found:**

| Severity | Issue                  | Description                                                                     |
| -------- | ---------------------- | ------------------------------------------------------------------------------- |
| Medium   | Active state too heavy | Solid primary background looks like error/alert. Dominates visual hierarchy.    |
| Medium   | No mode descriptions   | User doesn't know what "Agentic" or "Structure" modes do without checking docs. |
| Low      | No hover feedback      | Only background color change on hover, no ring or glow.                         |

**Proposed Redesign:**

```
┌────────────────────────┐
│                      │
│ ┌───┬───┬───┐      │
│ │🎙️│✨ │🔥 │      │  ← Active = outline + teal border
│ │Off│Lgt│Agr│      │     + subtle ring glow on hover
│ ├───┼───┼───┤      │
│ │🤖│✍️│💻 │      │
│ │Agt│Wrt│Cod │      │
│ ├───┼───┼───┤      │
│ │🏗️│👤│💎 │      │
│ │Str│Prs│Clr│      │
│ └───┴───┴───┘      │
│                      │
│ ┌────────────────┐    │
│ │ Current: Code │    │
│ │ Fast typing   │    │  ← Add description line
│ └────────────────┘    │
└────────────────────────┘
```

**Component-by-Component Breakdown:**

1. **Mode Buttons** (MODIFY)
   - **Before:** `variant="default"` for active (solid teal background)
   - **After:** New `variant="mode-active"` → outline border + teal primary color + subtle glow
   - **CSS:** `border: 2px solid hsl(159 84% 39%); box-shadow: 0 0 12px hsl(159 84% 39% / 0.3)`
   - **Rationale:** Solid background overwhelms. Outline is lighter, more modern.

2. **Mode Descriptions** (ADD)
   - **Before:** None
   - **After:** Either (a) subtitle line in status pill, or (b) tooltip on hover
   - **Recommendation:** Tooltip via shadcn/ui `<Tooltip>` component
   - **Rationale:** "Agentic", "Persona", "Structure" meaningless without context.

3. **Hover Feedback** (ENHANCE)
   - **Before:** Background color change
   - **After:** Add `ring-2 ring-primary/20 ring-offset-1` on hover
   - **Rationale:** Makes interactive elements feel more responsive and polished.

---

### Config Tab

**Current State:**

The Config tab uses collapsible sections (details/summary) with dense vertical stacking. All inputs are text fields (no file pickers). Everything is cramped with insufficient padding. Scrollbar covers elements making them unclickable.

```
┌────────────────────────┐
│ ▶ Audio & Transcr.   │
│ ▼ Audio Source       │  ← Section headers
│ ▼ Streaming Behav.   │
│ ▶ Features          │
│ ▶ Post-Processing   │
│ ▶ Voice Control      │
│ ▶ Advanced          │
│                      │
│ [dense form fields]   │  ← Cramped, insufficient padding
│                      │
│ [scrollbar overlaps]  │  ← Elements become unclickable
└────────────────────────┘
```

**Issues Found:**

| Severity | Issue                       | Description                                                         |
| -------- | --------------------------- | ------------------------------------------------------------------- |
| Critical | Insufficient padding        | Components touch scrollbar, become unclickable. Smashed vertically. |
| Critical | File paths as plain text    | No file pickers. Users must type absolute paths (`/home/jon/...`).    |
| Critical | Audio source text input     | Should be dropdown populated by `list_sources` command.               |
| High     | Absolute paths displayed    | Show `/home/jon/...` instead of `~/...`. Wastes space.                  |
| High     | Switches too small          | Hidden by scrollbar. Hard to click.                                 |
| High     | Post-processing dropdowns   | Full-width select for 9 options. Too large, clunky.                 |
| High     | Suppress regex single field | Cannot have multiple patterns. No naming, no toggling.              |
| Medium   | Voice control mode broken   | Config persistence bug. Changes don't apply.                        |
| Low      | Log file no picker          | Same as other file paths.                                           |

**Proposed Redesign:**

```
┌────────────────────────┐
│ ▶ Audio & Transcr.   │
│ ▶ Audio Source       │
│ ▶ Streaming Behav.   │
│ ▶ Features          │
│ ▶ Post-Processing   │
│ ▶ Voice Control      │
│ ▶ Advanced          │
│                      │
│ ▼ Audio & Transcr.   │  ← Section expanded
│                      │
│ Whisper CLI     [...]│  ← File input with picker button
│ Model          [...]│     (browse icon, shows `~/...`)
│ Language       [▼▼▼]│
│                      │
│ ▼ Audio Source       │
│                      │
│ Source        [▼▼▼]│  ← Dropdown from `list_sources`
│ Preferred     [...]│
│                      │
│ ▼ Features          │
│                      │
│ Real-time       [O] │  ← Switch with padding
│ Smart Punct.    [O] │     (larger, ring on focus)
│ Symbols         [O] │
│ Suppress NST    [O] │
│                      │
│ ▼ Post-Processing   │
│                      │
│ Enabled        [O]   │
│                      │
│ Mode:               │
│ ┌───┬───┬───┐    │
│ │...│...│...│    │  ← 3×3 grid (same as Modes tab)
│ ├───┼───┼───┤    │     Not full-width dropdown
│ │...│...│...│    │
│ └───┴───┴───┘    │
│                      │
│ Trigger        [▼▼▼]│
│                      │
│ ▶ Suppress Rules     │  ← NEW: Rules manager
│   (3 active, 2 off)│
│                      │
│ ┌────────────────┐    │
│ │ [+ Add Rule]   │    │
│ │                │    │
│ │ • Filter profanity│    │  ← Rule list with toggles
│ │   [✓] Active  │    │
│ │                │    │
│ │ • Remove filler │    │
│ │   [✗] Disabled│    │
│ │                │    │
│ │ • Custom: ...  │    │
│ │   [✓] Active  │    │
│ └────────────────┘    │
└────────────────────────┘
```

**Component-by-Component Breakdown:**

1. **Section Padding** (FIX)
   - **Before:** `space-y-2` (insufficient, scrollbar overlap)
   - **After:** `space-y-4`, add `pb-2` to each section
   - **Rationale:** Critical usability issue. Components must be fully clickable.

2. **File Picker Inputs** (NEW COMPONENT)
   - **Before:** Plain text input showing absolute paths
   - **After:** Composite component: text input + browse button (folder icon)
   - **Display:** Show `~/...` instead of `/home/jon/...`
   - **Implementation:** Use `@tauri-apps/plugin-dialog` for file dialog
   - **Props:** `{ label, value, onChange, filters, directory }`

3. **Audio Source Dropdown** (REPLACE)
   - **Before:** Text input field
   - **After:** `<Select>` populated by `invoke('list_sources')`
   - **Auto-select:** Detect system default mic and pre-select
   - **Rationale:** Users shouldn't type device names.

4. **Switch Component** (MODIFY)
   - **Before:** `h-6 w-11` (too small, ring focus issue)
   - **After:** `h-7 w-13` (larger thumb track), `ring-2 ring-primary ring-offset-2` on focus
   - **Rationale:** Hidden by scrollbar. Larger target improves accessibility.

5. **Post-Processing Mode** (REPLACE)
   - **Before:** Full-width `<Select>` with 9 options
   - **After:** Reuse `<ModeQuickSelect>` 3×3 grid
   - **Rationale:** Matches Modes tab. Full-width select is clunky.

6. **Suppress Rules Manager** (NEW COMPONENT)
   - **Before:** Single text input for regex pattern
   - **After:** Full rule manager with list view
   - **Data structure:**
     ```typescript
     interface SuppressRule {
       id: string;
       name: string;
       pattern: string;
       enabled: boolean;
       isBuiltIn: boolean;
     }
     ```
   - **UI:** List of rules with name, pattern preview, toggle switch, delete button (custom only)
   - **Built-in rules:** "Filter profanity", "Remove filler words", "Normalize whitespace"
   - **Add custom:** Opens dialog with name, pattern, test input
   - **Test feature:** Live regex tester to validate patterns

7. **Log File Input** (ADD FILE PICKER)
   - **Before:** Plain text input
   - **After:** File picker component (same as other file inputs)
   - **Rationale:** Consistency. Users shouldn't type paths.

---

### Global Window Management

**Current State:**

Window opens at fixed 320×480px. Min dimensions: 280×400px. Max: 350×800px. Single size for all tabs. Blank space at bottom of Status/Modes pages.

```
┌────────────────────────┐
│ [Status][Modes][Config]│  ← Fixed width: 320px
├────────────────────────┤
│                      │
│  [Tab content...]     │
│                      │
│                      │
│ [blank space...]      │  ← Status/Modes don't fill 480px
│                      │
│                      │
└────────────────────────┘
```

**Issues Found:**

| Severity | Issue                | Description                                                     |
| -------- | -------------------- | --------------------------------------------------------------- |
| Critical | Fixed width too wide | Opens at 320px, user wants 260px (min 280px - 20px margin).     |
| Critical | No per-tab sizing    | All tabs same height. Config needs ~600px, Status needs ~360px. |
| High     | No resize animation  | Jarring jump when switching tabs.                               |
| High     | Blank space wasted   | Status/Modes show empty area. Config scrolls prematurely.       |

**Proposed Redesign:**

```
Status tab → 260px × 360px
Modes tab  → 260px × 400px
Config tab → 260px × 600px (or scroll at 500px)
```

**Implementation:**

1. **Initial Window:**
   ```json
   {
     "width": 280,  // Min width
     "height": 400  // Min height
   }
   ```

2. **Tab-Specific Sizing:**
   ```typescript
   const tabSizes: Record<Tab, { width: number; height: number }> = {
     status: { width: 260, height: 360 },
     modes: { width: 260, height: 400 },
     config: { width: 260, height: 500 },  // Scroll after 500px
   };
   ```

3. **Animated Transition:**
   ```typescript
   useEffect(() => {
     const target = tabSizes[activeTab];
     invoke('set_window_size', { ...target });
   }, [activeTab]);
   ```

4. **CSS Transition:**
   ```css
   body {
     transition: width 300ms ease-out, height 300ms ease-out;
   }
   ```

**Rationale:** Dynamic sizing eliminates wasted space, makes each tab feel custom-fit. Smooth transition feels premium.

---

## Global Issues

### Component Library

**Issue 1: Insufficient Padding (CRITICAL)**

**Current:**
```tsx
<div className="space-y-2">
  <div className="space-y-1">
    <label>...</label>
    <Input />
  </div>
</div>
```

**Problem:** `space-y-2` between sections, `space-y-1` for form fields. Scrollbar overlaps last element making it unclickable.

**Fix:**
```tsx
<div className="space-y-4 pb-4">  {/* More spacing, bottom padding */}
  <div className="space-y-2">       {/* More space for fields */}
    <label className="mb-1">...</label>
    <Input className="mb-2" />
  </div>
</div>
```

**Issue 2: Buttons Too Wide (HIGH)**

**Current:** Full-width buttons (`flex-1`) look dated ("90s style").

**Fix:** Use constrained widths with consistent sizing:
```tsx
<Button className="w-24">Start</Button>
<Button variant="outline" className="w-10">↻</Button>
```

**Issue 3: Dropdown Transparency (HIGH)**

**Current:** Select dropdown has transparent background, items float on top of other content.

**Fix:** Add solid background to `SelectContent`:
```tsx
<SelectContent className="bg-popover border border-border shadow-lg">
  {/* Items */}
</SelectContent>
```

**Issue 4: Switch Component Too Small (HIGH)**

**Current:** `h-6 w-11` (24px × 44px). Thumb is 20px. Hard to click.

**Fix:**
```tsx
<Switch className="h-7 w-13">  {/* 28px × 52px */}
  <SwitchThumb className="h-6 w-6" />
</Switch>
```

**Issue 5: No Hover Glow (MEDIUM)**

**Current:** Hover only changes background color.

**Fix:** Add ring/shadow:
```tsx
<Button className="hover:ring-2 hover:ring-primary/20 hover:ring-offset-1">
```

**Issue 6: Font Size Inconsistency (LOW)**

**Current:** Mix of `text-xs`, `text-sm`, `text-[10px]` across components.

**Fix:** Establish strict hierarchy:
```css
--font-size-xs: 0.75rem;   /* 12px - captions */
--font-size-sm: 0.875rem;  /* 14px - labels */
--font-size-md: 1rem;      /* 16px - body */
--font-size-lg: 1.125rem;  /* 18px - headings */
```

---

## Component Library Recommendations

### Button Component

**Add New Variants:**

```typescript
const buttonVariants = cva(..., {
  variants: {
    variant: {
      ...existing,
      'mode-active': 'border-2 border-primary bg-transparent text-primary hover:bg-primary/10',
      'icon-only': 'h-8 w-8 p-0',
    },
  },
});
```

**Remove:** Full-width usage (`flex-1`) on action buttons.

### Switch Component

**Increase Size:**

```tsx
<SwitchPrimitives.Root className="h-7 w-13 ...">
  <SwitchPrimitives.Thumb className="h-6 w-6 ..." />
</SwitchPrimitives.Root>
```

**Add Focus Ring:**

```tsx
className="... focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
```

### Select Component

**Fix Transparency:**

```tsx
<SelectContent className="bg-popover border border-border shadow-lg">
```

**Add Hover Highlight:**

```tsx
<SelectItem className="hover:bg-accent hover:text-accent-foreground">
```

### Input Component

**Add File Picker Variant:**

```typescript
interface FileInputProps {
  label: string;
  value: string;
  onChange: (path: string) => void;
  filters?: { name: string; extensions: string[] }[];
  directory?: boolean;
}

export function FileInput({ label, value, onChange, filters, directory }: FileInputProps) {
  const handleBrowse = async () => {
    const selected = await invoke('open_dialog', { filters, directory });
    if (selected) onChange(selected);
  };

  const displayPath = value.replace(/^\/home\/[^\/]+/, '~');

  return (
    <div className="space-y-2">
      <label>{label}</label>
      <div className="flex gap-2">
        <Input value={displayPath} readOnly />
        <Button variant="outline" onClick={handleBrowse}>...</Button>
      </div>
    </div>
  );
}
```

---

## New Components Needed

### 1. Waveform Visualizer

**Purpose:** Real-time audio volume visualization on Status page.

**Spec:**
- 12-bar histogram
- Smooth 60fps animation
- Teal color (`--primary`) for active bars
- Gradient opacity (full at bottom, fade at top)
- Responsive to audio level from backend

**Implementation:**
```tsx
interface WaveformProps {
  level: number; // 0-1
  isActive: boolean;
}

export function Waveform({ level, isActive }: WaveformProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  useEffect(() => {
    // Animate based on level
  }, [level]);

  return <canvas ref={canvasRef} width={200} height={40} />;
}
```

### 2. Suppress Rules Manager

**Purpose:** Manage multiple named regex suppression rules.

**Spec:**
- List view of rules with name, pattern preview, toggle
- Add custom rule dialog
- Built-in rules (delete protected)
- Live regex tester

**Implementation:**
```tsx
interface RulesManagerProps {
  rules: SuppressRule[];
  onChange: (rules: SuppressRule[]) => void;
}

export function RulesManager({ rules, onChange }: RulesManagerProps) {
  return (
    <div>
      <RuleList rules={rules} onChange={onChange} />
      <AddRuleDialog onAdd={(rule) => onChange([...rules, rule])} />
    </div>
  );
}
```

### 3. File Picker Wrapper

**Purpose:** Reusable file input with browse button using Tauri dialog.

**Spec:**
- Text input (read-only) + browse button
- Display `~/...` instead of absolute path
- Support file filters
- Support directory mode

**Implementation:** See File Input component spec above.

### 4. Mode Badge

**Purpose:** Show current voice activation mode (toggle/hold) in Status page.

**Spec:**
- Small pill badge
- Text: "TOGGLE" or "HOLD"
- Position: Above status emoji
- Colors: Primary border, muted background

**Implementation:**
```tsx
export function ModeBadge({ mode }: { mode: 'toggle' | 'hold' }) {
  return (
    <div className="inline-flex items-center rounded-full border border-primary/50 bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
      {mode.toUpperCase()}
    </div>
  );
}
```

---

## Implementation Priority

### Phase 1: Critical Usability (Week 1)

1. **Window dynamic sizing** (2 days)
   - Add tab-specific sizes
   - Implement resize animation
   - Test on all three tabs

2. **Config tab padding** (1 day)
   - Increase section spacing
   - Add bottom padding
   - Verify scrollbar no longer overlaps

3. **File picker component** (2 days)
   - Create `FileInput` component
   - Integrate with `@tauri-apps/plugin-dialog`
   - Replace Whisper CLI, Model, Log File inputs

4. **Audio source dropdown** (1 day)
   - Fetch sources via `list_sources`
   - Populate `<Select>`
   - Auto-select system default

### Phase 2: Visual Feedback (Week 2)

5. **Waveform visualizer** (3 days)
   - Canvas-based component
   - Integrate with audio level from backend
   - Add to Status page

6. **Recording indicator** (1 day)
   - Add "Recording" state (vs "Listening")
   - Pulse animation on status emoji
   - Update status text

7. **Mode badge** (1 day)
   - Create `ModeBadge` component
   - Add to Status page
   - Pull current mode from config

### Phase 3: Component Library (Week 2-3)

8. **Switch component resize** (0.5 day)
   - Increase to `h-7 w-13`
   - Add focus ring
   - Test accessibility

9. **Button variants** (1 day)
   - Add `mode-active` variant
   - Add `icon-only` variant
   - Update Modes tab buttons

10. **Dropdown fix** (0.5 day)
   - Add solid background
   - Add hover highlight
   - Test transparency issue

### Phase 4: Config Enhancements (Week 3-4)

11. **Suppress rules manager** (5 days)
   - Create data structure
   - Build list view
   - Add rule dialog
   - Implement regex tester
   - Migrate existing config

12. **Post-processing grid** (1 day)
   - Reuse `ModeQuickSelect` in Config tab
   - Remove full-width dropdown

### Phase 5: Polish (Week 4)

13. **Mode descriptions** (2 days)
   - Add tooltip component
   - Write descriptions for all 8 modes
   - Add hover glow

14. **Footer cursor indicator** (0.5 day)
   - Add emoji pill to Status page
   - Show/hide based on config

15. **Reload button tooltip** (0.5 day)
   - Add "Refresh status" tooltip
   - Clarify always-enabled state

---

## Design System Updates

### New Spacing Tokens

```css
:root {
  --spacing-section: 1rem;      /* Space between sections */
  --spacing-section-lg: 1.5rem; /* Larger section gap */
  --spacing-field: 0.75rem;     /* Space between form fields */
  --spacing-field-lg: 1rem;     /* Larger field gap */
}
```

### New Component Variants

**Button:**
- `mode-active`: Outline with primary border
- `icon-only`: Fixed square size (32px)

**Switch:**
- `large`: Increased size for better clickability

### Updated Typography Hierarchy

```css
:root {
  --font-size-xs: 0.75rem;   /* 12px - captions, labels */
  --font-size-sm: 0.875rem;  /* 14px - body text, form labels */
  --font-size-md: 1rem;      /* 16px - headings */
  --font-size-lg: 1.125rem;  /* 18px - main headings */
  --font-size-xl: 1.25rem;   /* 20px - page titles */
}
```

### New Animation Tokens

```css
:root {
  --transition-window: 300ms ease-out;
  --transition-fast: 150ms ease-in-out;
  --transition-slow: 300ms ease-in-out;
}
```

### Color Enhancements

**Add glow/shadow colors:**
```css
:root {
  --primary-glow: hsla(159 84% 39% / 0.3);
  --primary-glow-strong: hsla(159 84% 39% / 0.5);
}
```

---

## What to Keep (User Preferences)

✅ **Default dark mode color scheme** - User explicitly likes this  
✅ **Emoji and icon usage** - "Overall concept and direction"  
✅ **Idle/recording animation** - Wants to enhance, not replace  
✅ **Card component structure** - Good foundation, needs padding fix  

---

## Technical Notes

### Tauri Integration Required

1. **Window resize command:**
   ```rust
   #[tauri::command]
   async fn set_window_size(width: u32, height: u32) -> Result<(), String> {
       // Implementation
   }
   ```

2. **Audio level stream:**
   ```rust
   // Emit audio level events for waveform
   app.emit("audio-level", level);
   ```

3. **File dialog plugin:**
   ```toml
   [dependencies]
   tauri-plugin-dialog = "2"
   ```

### Component Dependencies

- `@tauri-apps/plugin-dialog` for file pickers
- `@radix-ui/react-tooltip` for mode descriptions
- Canvas API for waveform
- Web Audio API (optional) for local fallback

---

## Conclusion

The easy-local-whisper-hotkey UI has solid foundations but suffers from several critical usability issues:

1. **Window sizing** forces wasted space across all tabs
2. **Config tab** is cramped, lacks file pickers, and has broken features
3. **Status page** misses essential visual feedback (waveform, recording state)
4. **Component library** has insufficient padding and dated styling

Implementing Phase 1 fixes will immediately improve user experience. Phase 2-4 enhancements will transform the app from "functional but rough" to "polished and delightful."

**Estimated effort:** 3-4 weeks for full implementation  
**User impact:** High — fixes critical friction points across entire app

---

**Next Steps:**
1. Review and approve report
2. Prioritize Phase 1 tasks
3. Begin with window dynamic sizing (highest impact)
