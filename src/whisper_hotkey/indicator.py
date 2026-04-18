import ctypes
import math
import os
import struct
import time
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    Image = None

INDICATOR_SIZE = 64
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
    def __init__(self, libx11, display, root_window, logger):
        self.libx11 = libx11
        self.display = display
        self.root = root_window
        self.logger = logger
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
        self._gradient_frames_path = None
        self._gradient_frames = []
        self._frame_count = 0
        self._current_frame_index = 0
        self._state = STATE_IDLE
        self._state_frames = {}
        self._setup_libs()
        self._setup_x11_signatures()
        self._create_window()
        self._load_all_frames()

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

    def _load_all_frames(self):
        frames_dir = Path(__file__).parent / "indicator_frames"
        if not frames_dir.exists():
            self.logger.log("CursorIndicator: indicator_frames directory not found, using solid fallback")
            return

        for state_name in [STATE_IDLE, STATE_RECORDING, STATE_PROCESSING]:
            state_dir = frames_dir / state_name
            if state_dir.exists():
                png_files = sorted(state_dir.glob("frame_*.png"))
                if png_files:
                    self._state_frames[state_name] = png_files
                    self.logger.log(f"CursorIndicator: loaded {len(png_files)} frames for {state_name} state")
                else:
                    self.logger.log(f"CursorIndicator: no frames found for {state_name} state")
            else:
                self.logger.log(f"CursorIndicator: state directory not found: {state_dir}")

        if not self._state_frames:
            self.logger.log("CursorIndicator: no state frames found, using backward-compatible gradient frames")
            png_files = sorted(frames_dir.glob("gradient_frame_*.png"))
            if png_files:
                self._state_frames[STATE_RECORDING] = png_files
                self.logger.log(f"CursorIndicator: loaded {len(png_files)} backward-compatible gradient frames")

        self._update_active_frames()

    def _update_active_frames(self):
        state_frames = self._state_frames.get(self._state)
        if state_frames:
            self._gradient_frames = state_frames
            self._frame_count = len(state_frames)
            self.logger.log(f"CursorIndicator: active state={self._state}, frames={self._frame_count}")
        else:
            self._gradient_frames = []
            self._frame_count = 0
            self.logger.log(f"CursorIndicator: no frames for state={self._state}, falling back to solid")

    def set_state(self, state: str):
        if state not in [STATE_IDLE, STATE_RECORDING, STATE_PROCESSING]:
            self.logger.log(f"CursorIndicator: invalid state={state}, ignoring")
            return

        if self._state != state:
            self._state = state
            self._update_active_frames()

    def _draw_gradient_frame(self, frame_index):
        if not self._picture or not self._ext_render or not self._gradient_frames or not HAS_PIL:
            return

        frame_path = self._gradient_frames[frame_index]

        try:
            img = Image.open(frame_path)
            if img.size != (INDICATOR_SIZE, INDICATOR_SIZE):
                img = img.resize((INDICATOR_SIZE, INDICATOR_SIZE), Image.Resampling.LANCZOS)

            if img.mode != "RGBA":
                img = img.convert("RGBA")

            for y in range(INDICATOR_SIZE):
                for x in range(INDICATOR_SIZE):
                    r, g, b, a = img.getpixel((x, y))
                    if a == 0:
                        continue

                    color = _XRenderColor(
                        red=int(r / 255 * 65535),
                        green=int(g / 255 * 65535),
                        blue=int(b / 255 * 65535),
                        alpha=int(a / 255 * 65535),
                    )
                    self._libxrender.XRenderFillRectangle(
                        self.display, PICT_OP_SRC, self._picture,
                        ctypes.byref(color), x, y, 1, 1,
                    )
        except Exception as e:
            self.logger.log(f"CursorIndicator: failed to draw frame {frame_index}: {e}")

    def tick(self):
        if not self._visible or not self._window:
            return

        if self._gradient_frames:
            phase = time.time() * 1.5
            pulse = math.sin(phase)
            frame_offset = int((pulse + 1) / 2 * self._frame_count) % self._frame_count
            self._current_frame_index = frame_offset
            self._draw_gradient_frame(frame_offset)
        else:
            phase = time.time() * 1.5
            pulse = math.sin(phase)
            self._draw(0.55 + 0.08 * pulse, 0.25 + 0.05 * pulse)

    def show(self):
        if not self._window:
            return
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
            self._pos_x = root_x.value - INDICATOR_SIZE // 2
            self._pos_y = root_y.value - INDICATOR_OFFSET_Y
        self.libx11.XMoveWindow(self.display, self._window, self._pos_x, self._pos_y)
        self._visible = True
        self.libx11.XMapWindow(self.display, self._window)
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
