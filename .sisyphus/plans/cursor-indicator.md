# Cursor Indicator — Pure X11/ctypes Overlay

## Architecture

**Single Display, single thread, no new dependencies.**

The overlay window reuses `self.libx11` and `self.display` from `X11HotkeyDaemon`. All X11 calls happen on the main thread inside the existing `handle_toggle_session()` and `handle_hold_session()` polling loops. No GTK, no python-xlib, no background threads.

### Why this works (after GTK rejection)

- GTK was rejected: main thread blocks in recording loops, `GLib.idle_add()` never fires
- python-xlib rejected: not installed, would need second X11 connection
- Pure ctypes: same Display, same thread, XRender for alpha drawing, XShape for click-through
- The polling loops already run at 20Hz (`time.sleep(0.05)`) — cursor tracking and animation happen there

## Implementation Steps

### Step 1: Create `indicator.py` module

New file: `src/whisper_hotkey/indicator.py`

```python
class CursorIndicator:
    """Pure X11/ctypes floating cursor indicator using XRender for alpha drawing."""
```

**Constructor**: `__init__(self, libx11, display, root_window, logger)`

Receives the existing ctypes X11 handle, display pointer, and root window. No new connections.

**Constants**:
```
INDICATOR_SIZE = 18        # pixels — half cursor height
INDICATOR_OFFSET_Y = 24    # pixels above cursor
SHAPE_BOUNDING = 0
SHAPE_INPUT = 2
SHAPE_SET = 0
PICT_OP_SRC = 1
```

### Step 2: Window creation — `_create_window()`

Uses `XCreateWindow` (not `XCreateSimpleWindow`) with:
- `override_redirect=1` — bypass window manager
- `save_under=1` — compositor hint for fast restore
- `border_pixel=0` — no border
- `background_pixel=0` — transparent background
- `colormap=default_colormap` — from default screen
- `event_mask=0` — no events (click-through)
- Size: `INDICATOR_SIZE x INDICATOR_SIZE` (18x18 pixels)

After creation:
- Set `_NET_WM_WINDOW_TYPE_DOCK` via `XChangeProperty`
- Set `_NET_WM_STATE_ABOVE` via `XChangeProperty`
- Call `XShapeCombineMask(window, SHAPE_INPUT, 0, 0, 0, SHAPE_SET)` for click-through
- Call `XMapWindow` to make visible (when shown)

**ctypes signatures needed** (all added to `indicator.py`):

```
XCreateWindow(display, parent, x, y, width, height, border_width, depth,
              class, visual, valuemask, attributes) -> Window
XMapWindow(display, window) -> int
XUnmapWindow(display, window) -> int
XMoveWindow(display, window, x, y) -> int
XDestroyWindow(display, window) -> int
XChangeProperty(display, window, property, type, format, mode, data, nelements) -> int
XInternAtom(display, name, only_if_exists) -> Atom
XShapeCombineMask(display, window, dest_kind, x_offset, y_offset, src, op) -> void
XRenderFillRectangle(display, op, dst, color, x, y, width, height) -> void
XRenderCreatePicture(display, drawable, format, valuemask, attributes) -> Picture
XRenderFindVisualFormat(display, visual) -> XRenderPictFormat*
XQueryPointer(display, window, root_return, child_return, root_x_return,
              root_y_return, win_x_return, win_y_return, mask_return) -> Bool
```

### Step 3: Circular shape mask — `_create_circle_mask()`

Creates a 1-bit pixmap (18x18) with a circle drawn via `XFillArc`. Used as `SHAPE_BOUNDING` mask so the rectangular window appears circular.

```
mask = XCreatePixmap(display, root, 18, 18, 1)
gc = XCreateGC(display, mask, 0, 0)
XSetForeground(display, gc, 0)
XFillRectangle(display, mask, gc, 0, 0, 18, 18)  # clear to transparent
XSetForeground(display, gc, 1)
XFillArc(display, mask, gc, 0, 0, 18, 18, 0, 360*64)  # filled circle
XShapeCombineMask(display, window, SHAPE_BOUNDING, 0, 0, mask, SHAPE_SET)
XFreePixmap(display, mask)
XFreeGC(display, gc)
```

### Step 4: Drawing — `_draw(alpha)`

Uses XRender to fill the circular window with semi-transparent yellow:

```python
def _draw(self, alpha: float):
    # alpha: 0.0 to 1.0
    # XRenderColor: 16-bit per channel (0-65535)
    color = XRenderColor(
        red=65535,      # 0xFFFF
        green=60395,    # 0xEB00-ish (warm yellow)
        blue=13056,     # 0x3300-ish
        alpha=int(alpha * 65535)
    )
    XRenderFillRectangle(display, PICT_OP_SRC, picture, &color, 0, 0, 18, 18)
```

**Note on XRenderPicture**: Created once during window creation:
```python
visual_format = XRenderFindVisualFormat(display, default_visual)
picture = XRenderCreatePicture(display, window, visual_format, 0, NULL)
```

### Step 5: Pulse animation — `tick()`

Called from the main thread's polling loop (every 50ms = 20Hz):

```python
def tick(self):
    """Called every 50ms from main thread. Handles animation and cursor tracking."""
    if not self._visible:
        return

    # Update cursor position
    root_x, root_y = self._query_pointer()
    win_x = root_x - INDICATOR_SIZE // 2
    win_y = root_y - INDICATOR_OFFSET_Y
    if win_x != self._last_x or win_y != self._last_y:
        XMoveWindow(display, window, win_x, win_y)
        self._last_x = win_x
        self._last_y = win_y

    # Pulse animation: sine wave between 0.4 and 0.9 alpha
    phase = time.time() * 2.0  # ~0.3Hz pulse (subtle)
    alpha = 0.65 + 0.25 * math.sin(phase)
    self._draw(alpha)
```

### Step 6: Public API

```python
def show(self):
    """Map window and start showing indicator."""
    self._visible = True
    XMapWindow(display, window)
    logger.log("Cursor indicator: shown")

def hide(self):
    """Unmap window and stop showing indicator."""
    self._visible = False
    XUnmapWindow(display, window)
    logger.log("Cursor indicator: hidden")

def destroy(self):
    """Destroy window and free resources."""
    if self._window:
        XUnmapWindow(display, self._window)
        XDestroyWindow(display, self._window)
        self._window = 0
    logger.log("Cursor indicator: destroyed")

def tick(self):
    """Called from main polling loop. Updates position and animation."""
```

### Step 7: Integration into app.py

**X11HotkeyDaemon.__init__** — add after `self._setup_xlib()`:
```python
self._indicator = None
self._indicator_enabled = True  # config flag
```

**X11HotkeyDaemon.open()** — add after display setup:
```python
if self._indicator_enabled:
    from whisper_hotkey.indicator import CursorIndicator
    self._indicator = CursorIndicator(
        libx11=self.libx11,
        display=self.display,
        root_window=self.root,
        logger=self.logger,
    )
    self.logger.log("Cursor indicator initialized")
```

**X11HotkeyDaemon.close()** — add before closing display:
```python
if self._indicator:
    self._indicator.destroy()
    self._indicator = None
```

**handle_toggle_session()** — show/hide in the recording loop:

Start of recording (line ~1059):
```python
if self._indicator:
    self._indicator.show()
```

In the polling loop (line ~1080, inside `while self.running and self.recording_active`):
```python
if self._indicator:
    self._indicator.tick()
```

Stop of recording (line ~1038):
```python
if self._indicator:
    self._indicator.hide()
```

**handle_hold_session()** — show/hide in the recording loop:

Start of recording (after `recorder.start()`):
```python
if self._indicator:
    self._indicator.show()
```

In the polling loop (line ~1129, inside `while self.running and not key_released`):
```python
if self._indicator:
    self._indicator.tick()
```

End of recording (after `transcriber.join()`):
```python
if self._indicator:
    self._indicator.hide()
```

### Step 8: Configuration

Add to `whisper-hotkey.env`:
```
WHISPER_INDICATOR=true
```

Add to `parse_args()`:
```python
parser.add_argument(
    "--indicator",
    action="store_true",
    default=os.environ.get("WHISPER_INDICATOR", "true").lower() == "true",
    help="Show a cursor indicator when recording.",
)
```

Pass through to `X11HotkeyDaemon`.

## Threading Safety Analysis

| Concern | Resolution |
|---------|-----------|
| Multiple X11 connections | **No** — reuses single Display from daemon |
| XInitThreads needed | **No** — all X11 calls on main thread |
| GTK threading violations | **No** — no GTK used |
| Main thread blocked | **No problem** — `tick()` runs inside the blocking loop |
| Race conditions | **No** — single-threaded, no shared mutable state across threads |
| Logger thread safety | **Safe** — Logger uses internal Lock |

## Dependency Check

| Dependency | Status |
|-----------|--------|
| libX11.so.6 | Already loaded |
| libXext.so.6 (XShape) | System library, ctypes load |
| libXrender.so.1 | System library, ctypes load |
| python-xlib | NOT needed |
| python3-gi/GTK | NOT needed |
| python3-cairo | NOT needed |

## Error Handling

1. **libXext/libXrender not available**: Try loading, catch OSError, log warning, disable indicator
2. **XRenderFindVisualFormat returns NULL**: Fall back to opaque fill, log warning
3. **XQueryPointer fails**: Skip position update for that tick
4. **Window creation fails**: Log error, set `_indicator = None`, continue without indicator

## Verification Plan

### Before implementation:
- `lsp_diagnostics` clean on indicator.py
- `python -c "from whisper_hotkey.indicator import CursorIndicator"` imports successfully

### After integration:
- `lsp_diagnostics` clean on app.py
- `systemctl --user restart whisper-hotkey.service`
- Check logs: `tail -f /tmp/whisper_hotkey.log` for "Cursor indicator: initialized"

### Manual testing:
1. Start daemon: `easy-local-whisper-hotkey run`
2. Press Ctrl+Space to start recording
3. **Should see**: Small yellow circle (~18px) floating above cursor, pulsing subtly
4. **Should NOT**: Block any clicks, appear in taskbar, steal focus
5. Move cursor around — indicator should follow smoothly
6. Press Ctrl+Space again to stop recording
7. **Should see**: Indicator disappears immediately
8. Speak into mic — text should appear as before, indicator visible while recording

### Expected log output:
```
[timestamp] Cursor indicator initialized
[timestamp] Ctrl+Space pressed; starting toggle session
[timestamp] Cursor indicator: shown
[timestamp] Cursor indicator: hidden
[timestamp] Ctrl+Space pressed; stopping toggle session
```

## Atomic Commits

1. **Add indicator.py** — CursorIndicator class with window creation, drawing, tick, show/hide
2. **Integrate into app.py** — Wire up indicator in daemon lifecycle and recording loops
3. **Add config flag** — --indicator arg and WHISPER_INDICATOR env var
