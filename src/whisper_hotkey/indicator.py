import ctypes
import math
import threading

INDICATOR_SIZE = 14
INDICATOR_OFFSET_Y = 24

STATE_IDLE = "idle"
STATE_RECORDING = "recording"
STATE_PROCESSING = "processing"

SHAPE_BOUNDING = 0
SHAPE_INPUT = 2
SHAPE_SET = 0
PICT_OP_SRC = 1
CW_BORDER_PIXEL = 1 << 3
CW_BACK_PIXEL = 1 << 1
CW_OVERRIDE_REDIRECT = 1 << 9
CW_SAVE_UNDER = 1 << 15
CW_EVENT_MASK = 1 << 11
CW_COLORMAP = 1 << 13
PROP_MODE_REPLACE = 0
XA_ATOM = 4
PIXMAP_NONE = 0
ZPixmap = 2


class CaretTracker:
    """Tracks text caret position via AT-SPI accessibility events."""

    def __init__(self, logger):
        self.logger = logger
        self._x = None
        self._y = None
        self._lock = threading.Lock()
        self._thread = None
        self._running = False
        self._loop = None
        self._caret_listener = None
        self._focus_listener = None

    def start(self):
        try:
            import gi
            gi.require_version('Atspi', '2.0')
            from gi.repository import Atspi, GLib
        except (ImportError, ValueError) as exc:
            self.logger.log(f"CaretTracker: AT-SPI unavailable ({exc}), using mouse fallback")
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.logger.log("CaretTracker: AT-SPI listener started")

    def stop(self):
        self._running = False
        if self._loop:
            try:
                self._loop.quit()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=3)
        self.logger.log("CaretTracker: stopped")

    def get_position(self):
        """Return cached (x, y) or None if no caret position known."""
        with self._lock:
            if self._x is not None and self._y is not None:
                return (self._x, self._y)
        return None

    def _on_caret_moved(self, event):
        try:
            src = event.source
            if not src or not src.is_text():
                return
            offset = src.get_caret_offset()
            char_count = src.get_character_count()
            if offset < 0:
                return
            if offset >= char_count:
                offset = max(0, char_count - 1)
            rect = src.get_character_extents(offset, 0)
            x, y, width, height = rect.x, rect.y, rect.width, rect.height
            if x <= -2147483648 or y <= -2147483648:
                return
            with self._lock:
                self._x = x
                self._y = y
            self.logger.log(f"CaretTracker: caret at ({x}, {y})")
        except Exception as exc:
            self.logger.log(f"CaretTracker: caret error: {exc}")

    def _on_focus_changed(self, event):
        if not event.detail1:
            return
        try:
            src = event.source
            if not src or not src.is_text():
                return
            offset = src.get_caret_offset()
            char_count = src.get_character_count()
            if offset < 0:
                return
            if offset >= char_count:
                offset = max(0, char_count - 1)
            rect = src.get_character_extents(offset, 0)
            x, y, width, height = rect.x, rect.y, rect.width, rect.height
            if x <= -2147483648 or y <= -2147483648:
                return
            with self._lock:
                self._x = x + width
                self._y = y
            self.logger.log(f"CaretTracker: focus at ({x}, {y})")
        except Exception as exc:
            self.logger.log(f"CaretTracker: focus error: {exc}")

    def _run_loop(self):
        try:
            import gi
            gi.require_version('Atspi', '2.0')
            from gi.repository import Atspi, GLib

            self._caret_listener = Atspi.EventListener.new(self._on_caret_moved)
            self._focus_listener = Atspi.EventListener.new(self._on_focus_changed)

            Atspi.EventListener.register(self._caret_listener, 'object:text-caret-moved')
            Atspi.EventListener.register(self._focus_listener, 'object:state-changed:focused')

            self._loop = GLib.MainLoop()
            self._loop.run()
        except Exception as exc:
            self.logger.log(f"CaretTracker: event loop failed ({exc})")
        finally:
            try:
                if self._caret_listener:
                    Atspi.EventListener.deregister(self._caret_listener, 'object:text-caret-moved')
                if self._focus_listener:
                    Atspi.EventListener.deregister(self._focus_listener, 'object:state-changed:focused')
            except Exception:
                pass


class _XImage(ctypes.Structure):
    _fields_ = [
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
        ("xoffset", ctypes.c_int),
        ("format", ctypes.c_int),
        ("byte_order", ctypes.c_int),
        ("data", ctypes.POINTER(ctypes.c_ubyte)),
    ]


class _XRenderColor(ctypes.Structure):
    _fields_ = [
        ("red", ctypes.c_ushort),
        ("green", ctypes.c_ushort),
        ("blue", ctypes.c_ushort),
        ("alpha", ctypes.c_ushort),
    ]


class _XSetWindowAttributes(ctypes.Structure):
    _fields_ = [
        ("background_pixmap", ctypes.c_ulong),
        ("background_pixel", ctypes.c_ulong),
        ("border_pixmap", ctypes.c_ulong),
        ("border_pixel", ctypes.c_ulong),
        ("bit_gravity", ctypes.c_int),
        ("win_gravity", ctypes.c_int),
        ("backing_store", ctypes.c_int),
        ("backing_planes", ctypes.c_ulong),
        ("backing_pixel", ctypes.c_ulong),
        ("save_under", ctypes.c_int),
        ("event_mask", ctypes.c_long),
        ("do_not_propagate_mask", ctypes.c_long),
        ("override_redirect", ctypes.c_int),
        ("colormap", ctypes.c_ulong),
        ("cursor", ctypes.c_ulong),
    ]


class CursorIndicator:
    def __init__(self, libx11, display, root_window, logger, caret_tracker=None):
        self.libx11 = libx11
        self.display = display
        self.root = root_window
        self.logger = logger
        self._caret_tracker = caret_tracker
        self._window = 0
        self._picture = 0
        self._visible = False
        self._pos_x = 0
        self._pos_y = 0
        self._libxext = None
        self._libxrender = None
        self._ext_shape = False
        self._ext_render = False
        self._argb_visual = None
        self._shape_pixmap = 0
        self._shape_gc = None
        self._window_gc = None
        self._setup_libs()
        self._setup_x11_signatures()
        self._create_window()
        self._create_static_bitmap()
        self._create_static_bitmap()

    def _setup_libs(self):
        try:
            self._libxext = ctypes.cdll.LoadLibrary("libXext.so.6")
            self._ext_shape = True
            self.logger.log("CursorIndicator: libXext loaded (XShape available)")
        except OSError:
            self.logger.log("CursorIndicator: libXext not available, no click-through")
        try:
            self._libxrender = ctypes.cdll.LoadLibrary("libXrender.so.1")
            self._ext_render = True
            self.logger.log("CursorIndicator: libXrender loaded (alpha drawing available)")
        except OSError:
            self.logger.log("CursorIndicator: libXrender not available, using opaque fallback")

    def _setup_x11_signatures(self):
        lib = self.libx11
        lib.XCreateWindow.argtypes = [
            ctypes.c_void_p, ctypes.c_ulong,
            ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_uint,
            ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p,
            ctypes.c_ulong, ctypes.POINTER(_XSetWindowAttributes),
        ]
        lib.XCreateWindow.restype = ctypes.c_ulong
        lib.XMapWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        lib.XMapWindow.restype = ctypes.c_int
        lib.XUnmapWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        lib.XUnmapWindow.restype = ctypes.c_int
        lib.XMoveWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int]
        lib.XMoveWindow.restype = ctypes.c_int
        lib.XDestroyWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        lib.XDestroyWindow.restype = ctypes.c_int
        lib.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        lib.XInternAtom.restype = ctypes.c_ulong
        lib.XChangeProperty.argtypes = [
            ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong,
            ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_ulong), ctypes.c_int,
        ]
        lib.XChangeProperty.restype = ctypes.c_int
        lib.XDefaultVisual.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.XDefaultVisual.restype = ctypes.c_void_p
        lib.XDefaultColormap.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.XDefaultColormap.restype = ctypes.c_ulong
        lib.XDefaultScreen.argtypes = [ctypes.c_void_p]
        lib.XDefaultScreen.restype = ctypes.c_int
        lib.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        lib.XDefaultRootWindow.restype = ctypes.c_ulong
        lib.XCreateGC.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p]
        lib.XCreateGC.restype = ctypes.c_void_p
        lib.XFreeGC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        lib.XCreatePixmap.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint]
        lib.XCreatePixmap.restype = ctypes.c_ulong
        lib.XFreePixmap.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        lib.XFreePixmap.restype = ctypes.c_int
        lib.XSetForeground.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
        lib.XFillRectangle.argtypes = [
            ctypes.c_void_p, ctypes.c_ulong, ctypes.c_void_p,
            ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_uint,
        ]
        lib.XFillArc.argtypes = [
            ctypes.c_void_p, ctypes.c_ulong, ctypes.c_void_p,
            ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_uint,
            ctypes.c_int, ctypes.c_int,
        ]
        lib.XCopyArea.argtypes = [
            ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p,
            ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_uint,
            ctypes.c_int, ctypes.c_int,
        ]
        lib.XCopyArea.restype = ctypes.c_int
        lib.XQueryPointer.argtypes = [
            ctypes.c_void_p, ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_uint),
        ]
        lib.XQueryPointer.restype = ctypes.c_int
        lib.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.XSync.restype = ctypes.c_int

        if self._ext_shape and self._libxext:
            self._libxext.XShapeCombineMask.argtypes = [
                ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int,
                ctypes.c_int, ctypes.c_int, ctypes.c_ulong, ctypes.c_int,
            ]

        if self._ext_render and self._libxrender:
            self._libxrender.XRenderFillRectangle.argtypes = [
                ctypes.c_void_p, ctypes.c_int, ctypes.c_ulong,
                ctypes.POINTER(_XRenderColor),
                ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_uint,
            ]
            self._libxrender.XRenderCreatePicture.argtypes = [
                ctypes.c_void_p, ctypes.c_ulong, ctypes.c_void_p,
                ctypes.c_ulong, ctypes.c_void_p,
            ]
            self._libxrender.XRenderCreatePicture.restype = ctypes.c_ulong
            self._libxrender.XRenderFindVisualFormat.argtypes = [
                ctypes.c_void_p, ctypes.c_void_p,
            ]
            self._libxrender.XRenderFindVisualFormat.restype = ctypes.c_void_p

    def _find_argb_visual(self, screen):
        if not self._ext_render or not self._libxrender:
            return None

        class _XVisualInfo(ctypes.Structure):
            _fields_ = [
                ("visual", ctypes.c_void_p),
                ("visualid", ctypes.c_ulong),
                ("screen", ctypes.c_int),
                ("depth", ctypes.c_int),
                ("c_class", ctypes.c_int),
                ("red_mask", ctypes.c_ulong),
                ("green_mask", ctypes.c_ulong),
                ("blue_mask", ctypes.c_ulong),
                ("colormap_size", ctypes.c_int),
                ("bits_per_rgb", ctypes.c_int),
            ]

        if not hasattr(self.libx11, '_vi_setup'):
            self.libx11.XGetVisualInfo.argtypes = [
                ctypes.c_void_p, ctypes.c_long, ctypes.POINTER(_XVisualInfo), ctypes.POINTER(ctypes.c_int),
            ]
            self.libx11.XGetVisualInfo.restype = ctypes.POINTER(_XVisualInfo)
            self.libx11.XFree.argtypes = [ctypes.c_void_p]
            self.libx11.XFree.restype = ctypes.c_int
            self.libx11._vi_setup = True

        template = _XVisualInfo()
        template.screen = screen
        template.depth = 32
        template.c_class = 4  # TrueColor
        count = ctypes.c_int()
        visuals = self.libx11.XGetVisualInfo(
            self.display, 0x2 | 0x4 | 0x8,
            ctypes.byref(template), ctypes.byref(count),
        )
        if not visuals or count.value == 0:
            if visuals:
                self.libx11.XFree(visuals)
            return None

        result = None
        for i in range(count.value):
            vi = visuals[i]
            if vi.depth == 32:
                fmt = self._libxrender.XRenderFindVisualFormat(self.display, vi.visual)
                if fmt:
                    result = vi.visual
                    break

        self.libx11.XFree(visuals)
        return result

    def _create_window(self):
        screen = self.libx11.XDefaultScreen(self.display)
        visual = self.libx11.XDefaultVisual(self.display, screen)
        colormap = self.libx11.XDefaultColormap(self.display, screen)
        depth = 24
        self._argb_visual = None

        if self._ext_render and self._libxrender:
            argb_visual = self._find_argb_visual(screen)
            if argb_visual:
                visual = argb_visual
                depth = 32
                self._argb_visual = argb_visual
                self.libx11.XCreateColormap.argtypes = [
                    ctypes.c_void_p, ctypes.c_ulong, ctypes.c_void_p, ctypes.c_int,
                ]
                self.libx11.XCreateColormap.restype = ctypes.c_ulong
                colormap = self.libx11.XCreateColormap(self.display, self.root, visual, 0)
                self.logger.log("CursorIndicator: using 32-bit ARGB visual")
            else:
                self.logger.log("CursorIndicator: no ARGB visual found, using default 24-bit")

        attrs = _XSetWindowAttributes()
        attrs.background_pixel = 0
        attrs.border_pixel = 0
        attrs.override_redirect = 1
        attrs.save_under = 1
        attrs.event_mask = 0
        attrs.colormap = colormap

        valuemask = (
            CW_BACK_PIXEL | CW_BORDER_PIXEL | CW_OVERRIDE_REDIRECT
            | CW_SAVE_UNDER | CW_EVENT_MASK | CW_COLORMAP
        )

        self._window = self.libx11.XCreateWindow(
            self.display, self.root,
            0, 0, INDICATOR_SIZE, INDICATOR_SIZE,
            0, ctypes.c_uint(depth), 1, visual,
            valuemask, ctypes.byref(attrs),
        )
        if not self._window:
            self.logger.log("CursorIndicator: FAILED to create window")
            return

        self._set_window_dock()
        self._set_window_above()
        self._make_click_through()
        self._create_circle_shape()
        self._create_render_picture()
        self.logger.log(f"CursorIndicator: window created id={self._window:#x} depth={depth}")

    def _set_window_dock(self):
        atom_type = self.libx11.XInternAtom(self.display, b"_NET_WM_WINDOW_TYPE", 0)
        atom_dock = self.libx11.XInternAtom(self.display, b"_NET_WM_WINDOW_TYPE_DOCK", 0)
        atom_val = ctypes.c_ulong(atom_dock)
        self.libx11.XChangeProperty(
            self.display, self._window,
            atom_type, XA_ATOM, 32, PROP_MODE_REPLACE,
            ctypes.byref(atom_val), 1,
        )

    def _set_window_above(self):
        atom_state = self.libx11.XInternAtom(self.display, b"_NET_WM_STATE", 0)
        atom_above = self.libx11.XInternAtom(self.display, b"_NET_WM_STATE_ABOVE", 0)
        atom_val = ctypes.c_ulong(atom_above)
        self.libx11.XChangeProperty(
            self.display, self._window,
            atom_state, XA_ATOM, 32, PROP_MODE_REPLACE,
            ctypes.byref(atom_val), 1,
        )

    def _make_click_through(self):
        if not self._ext_shape or not self._libxext:
            return
        self._libxext.XShapeCombineMask(
            self.display, self._window, SHAPE_INPUT, 0, 0, PIXMAP_NONE, SHAPE_SET,
        )
        self.logger.log("CursorIndicator: click-through enabled")

    def _create_circle_shape(self):
        if not self._ext_shape or not self._libxext:
            return
        self._shape_pixmap = self.libx11.XCreatePixmap(
            self.display, self.root, INDICATOR_SIZE, INDICATOR_SIZE, 1,
        )
        if not self._shape_pixmap:
            return
        self._shape_gc = self.libx11.XCreateGC(self.display, self._shape_pixmap, 0, None)
        if not self._shape_gc:
            self.libx11.XFreePixmap(self.display, self._shape_pixmap)
            self._shape_pixmap = 0
            return
        self.libx11.XSetForeground(self.display, self._shape_gc, 0)
        self.libx11.XFillRectangle(
            self.display, self._shape_pixmap, self._shape_gc,
            0, 0, INDICATOR_SIZE, INDICATOR_SIZE,
        )
        self.libx11.XSetForeground(self.display, self._shape_gc, 1)
        self.libx11.XFillArc(
            self.display, self._shape_pixmap, self._shape_gc,
            0, 0, INDICATOR_SIZE, INDICATOR_SIZE,
            0, 360 * 64,
        )
        self._libxext.XShapeCombineMask(
            self.display, self._window, SHAPE_BOUNDING, 0, 0,
            self._shape_pixmap, SHAPE_SET,
        )
        self.logger.log("CursorIndicator: circle shape applied")

    def _create_render_picture(self):
        if not self._ext_render or not self._libxrender:
            return
        visual = self._argb_visual
        if not visual:
            screen = self.libx11.XDefaultScreen(self.display)
            visual = self.libx11.XDefaultVisual(self.display, screen)
        fmt = self._libxrender.XRenderFindVisualFormat(self.display, visual)
        if not fmt:
            self.logger.log("CursorIndicator: XRenderFindVisualFormat returned NULL, no alpha drawing")
            return
        self._picture = self._libxrender.XRenderCreatePicture(
            self.display, self._window, fmt, 0, None,
        )
        self.logger.log(f"CursorIndicator: XRender picture created id={self._picture:#x}")

    def _create_static_bitmap(self):
        self._window_gc = self.libx11.XCreateGC(self.display, self._window, 0, None)
        if self._window_gc:
            self.logger.log("CursorIndicator: window GC created")

    def _draw_static_indicator(self):
        if self._picture and self._ext_render and self._libxrender:
            self._draw_gradient()
        elif self._window_gc:
            self._draw_fallback()

    def _draw_gradient(self):
        size = INDICATOR_SIZE
        center = size / 2
        max_r = size / 2 - 1
        base_r, base_g, base_b = 14, 165, 233
        bright_r, bright_g, bright_b = 125, 211, 252

        clear = _XRenderColor(red=0, green=0, blue=0, alpha=0)
        self._libxrender.XRenderFillRectangle(
            self.display, PICT_OP_SRC, self._picture,
            ctypes.byref(clear), 0, 0, size, size,
        )

        for y in range(size):
            for x in range(size):
                dx = x - center + 0.5
                dy = y - center + 0.5
                dist = math.sqrt(dx * dx + dy * dy)
                if dist > max_r:
                    continue

                t = dist / max_r
                falloff = max(0.0, 1.0 - t ** 1.5) * 0.92

                r = int(bright_r + (base_r - bright_r) * t)
                g = int(bright_g + (base_g - bright_g) * t)
                b = int(bright_b + (base_b - bright_b) * t)

                color = _XRenderColor(
                    red=int(r / 255 * 65535),
                    green=int(g / 255 * 65535),
                    blue=int(b / 255 * 65535),
                    alpha=int(falloff * 65535),
                )
                self._libxrender.XRenderFillRectangle(
                    self.display, PICT_OP_SRC, self._picture,
                    ctypes.byref(color), x, y, 1, 1,
                )

        self.libx11.XSync(self.display, 0)

    def _draw_fallback(self):
        if not self._window_gc:
            return
        self.libx11.XSetForeground(self.display, self._window_gc, 0)
        self.libx11.XFillRectangle(
            self.display, self._window, self._window_gc,
            0, 0, INDICATOR_SIZE, INDICATOR_SIZE,
        )
        self.libx11.XSetForeground(self.display, self._window_gc, 65535)
        self.libx11.XFillArc(
            self.display, self._window, self._window_gc,
            1, 1, INDICATOR_SIZE - 2, INDICATOR_SIZE - 2,
            0, 360 * 64,
        )
        self.libx11.XSync(self.display, 0)

    def tick(self):
        pass

    def show(self):
        if not self._window:
            return

        target_x, target_y = None, None
        if self._caret_tracker:
            pos = self._caret_tracker.get_position()
            if pos:
                target_x, target_y = pos
                self.logger.log(f"CursorIndicator: using caret position ({target_x}, {target_y})")

        if target_x is None:
            root_ret = ctypes.c_ulong()
            child_ret = ctypes.c_ulong()
            root_x = ctypes.c_int()
            root_y = ctypes.c_int()
            win_x = ctypes.c_int()
            win_y = ctypes.c_int()
            mask_ret = ctypes.c_uint()
            ok = self.libx11.XQueryPointer(
                self.display, self.root,
                ctypes.byref(root_ret), ctypes.byref(child_ret),
                ctypes.byref(root_x), ctypes.byref(root_y),
                ctypes.byref(win_x), ctypes.byref(win_y),
                ctypes.byref(mask_ret),
            )
            if ok:
                target_x = root_x.value
                target_y = root_y.value
                self.logger.log(f"CursorIndicator: using mouse position ({target_x}, {target_y})")

        if target_x is not None:
            self._pos_x = target_x - INDICATOR_SIZE // 2
            self._pos_y = target_y - INDICATOR_OFFSET_Y

        self.libx11.XMoveWindow(self.display, self._window, self._pos_x, self._pos_y)
        self._visible = True
        self.libx11.XMapWindow(self.display, self._window)
        self._draw_static_indicator()
        self.logger.log("CursorIndicator: shown")

    def hide(self):
        if not self._window:
            return
        self._visible = False
        if self._picture and self._ext_render and self._libxrender:
            clear = _XRenderColor(red=0, green=0, blue=0, alpha=0)
            self._libxrender.XRenderFillRectangle(
                self.display, PICT_OP_SRC, self._picture,
                ctypes.byref(clear), 0, 0, INDICATOR_SIZE, INDICATOR_SIZE,
            )
        self.libx11.XUnmapWindow(self.display, self._window)
        self.libx11.XSync(self.display, 0)
        self.logger.log("CursorIndicator: hidden")

    def destroy(self):
        if self._window_gc:
            self.libx11.XFreeGC(self.display, self._window_gc)
            self._window_gc = None
        if self._shape_gc:
            self.libx11.XFreeGC(self.display, self._shape_gc)
            self._shape_gc = None
        if self._shape_pixmap:
            self.libx11.XFreePixmap(self.display, self._shape_pixmap)
            self._shape_pixmap = 0
        if self._window:
            self.libx11.XUnmapWindow(self.display, self._window)
            self.libx11.XDestroyWindow(self.display, self._window)
            self.logger.log(f"CursorIndicator: destroyed window={self._window:#x}")
            self._window = 0
        self._picture = 0
