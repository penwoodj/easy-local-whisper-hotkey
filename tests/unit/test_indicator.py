import unittest
from unittest.mock import Mock, patch, MagicMock

from whisper_hotkey.indicator import CaretTracker, CursorIndicator


class CaretTrackerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_logger = Mock()

    def test_caret_tracker_init(self) -> None:
        tracker = CaretTracker(self.mock_logger)
        self.assertEqual(tracker.logger, self.mock_logger)
        self.assertIsNone(tracker._x)
        self.assertIsNone(tracker._y)
        self.assertIsNotNone(tracker._lock)
        self.assertIsNone(tracker._thread)
        self.assertFalse(tracker._running)
        self.assertIsNone(tracker._loop)
        self.assertIsNone(tracker._caret_listener)
        self.assertIsNone(tracker._focus_listener)

    def test_caret_tracker_get_position_none(self) -> None:
        tracker = CaretTracker(self.mock_logger)
        result = tracker.get_position()
        self.assertIsNone(result)

    def test_caret_tracker_get_position_cached(self) -> None:
        tracker = CaretTracker(self.mock_logger)
        tracker._x = 100
        tracker._y = 200
        result = tracker.get_position()
        self.assertEqual(result, (100, 200))

    @patch('threading.Thread')
    def test_caret_tracker_start_no_atspi(self, mock_thread) -> None:
        tracker = CaretTracker(self.mock_logger)
        with patch('builtins.__import__', side_effect=ImportError("gi not found")):
            tracker.start()
        self.mock_logger.log.assert_called()
        self.mock_logger.log.assert_any_call(
            unittest.mock.ANY
        )
        self.assertFalse(tracker._running)
        mock_thread.assert_not_called()

    @patch('threading.Thread')
    def test_caret_tracker_start_with_atspi(self, mock_thread) -> None:
        tracker = CaretTracker(self.mock_logger)
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance

        mock_gi = MagicMock()
        mock_atspi = MagicMock()
        mock_glib = MagicMock()
        mock_gi.require_version = Mock()
        mock_gi.repository.Atspi = mock_atspi
        mock_gi.repository.GLib = mock_glib
        mock_glib.MainLoop = Mock()
        mock_glib.MainLoop.return_value = MagicMock()

        with patch.dict('sys.modules', {'gi': mock_gi, 'gi.repository': mock_gi.repository, 'gi.repository.Atspi': mock_atspi, 'gi.repository.GLib': mock_glib}):
            import sys
            if 'gi' in sys.modules:
                del sys.modules['gi']
            tracker.start()

        self.assertTrue(tracker._running)
        mock_thread.assert_called_once()
        self.mock_logger.log.assert_called_with("CaretTracker: AT-SPI listener started")

    def test_caret_tracker_stop(self) -> None:
        tracker = CaretTracker(self.mock_logger)
        tracker._running = True
        mock_loop = Mock()
        tracker._loop = mock_loop
        mock_thread = Mock()
        tracker._thread = mock_thread

        tracker.stop()

        self.assertFalse(tracker._running)
        mock_loop.quit.assert_called_once()
        mock_thread.join.assert_called_once_with(timeout=3)
        self.mock_logger.log.assert_called_with("CaretTracker: stopped")

    def test_caret_tracker_stop_no_loop(self) -> None:
        tracker = CaretTracker(self.mock_logger)
        tracker._running = True
        tracker._loop = None
        mock_thread = Mock()
        tracker._thread = mock_thread

        tracker.stop()

        self.assertFalse(tracker._running)
        mock_thread.join.assert_called_once_with(timeout=3)

    def test_caret_tracker_stop_exception(self) -> None:
        tracker = CaretTracker(self.mock_logger)
        tracker._running = True
        mock_loop = Mock()
        mock_loop.quit.side_effect = Exception("quit failed")
        tracker._loop = mock_loop
        mock_thread = Mock()
        tracker._thread = mock_thread

        tracker.stop()

        self.assertFalse(tracker._running)
        mock_thread.join.assert_called_once_with(timeout=3)

    def test_caret_tracker_on_caret_moved(self) -> None:
        tracker = CaretTracker(self.mock_logger)
        mock_event = Mock()
        mock_source = Mock()
        mock_source.is_text.return_value = True
        mock_source.get_caret_offset.return_value = 5
        mock_source.get_character_count.return_value = 10
        mock_rect = Mock()
        mock_rect.x = 100
        mock_rect.y = 200
        mock_rect.width = 10
        mock_rect.height = 15
        mock_source.get_character_extents.return_value = mock_rect
        mock_event.source = mock_source

        tracker._on_caret_moved(mock_event)

        self.assertEqual(tracker._x, 100)
        self.assertEqual(tracker._y, 200)

    def test_caret_tracker_on_caret_moved_no_text(self) -> None:
        tracker = CaretTracker(self.mock_logger)
        tracker._x = 100
        tracker._y = 200
        mock_event = Mock()
        mock_source = Mock()
        mock_source.is_text.return_value = False
        mock_event.source = mock_source

        tracker._on_caret_moved(mock_event)

        self.assertEqual(tracker._x, 100)
        self.assertEqual(tracker._y, 200)

    def test_caret_tracker_on_caret_moved_negative_offset(self) -> None:
        tracker = CaretTracker(self.mock_logger)
        tracker._x = 100
        tracker._y = 200
        mock_event = Mock()
        mock_source = Mock()
        mock_source.is_text.return_value = True
        mock_source.get_caret_offset.return_value = -1
        mock_event.source = mock_source

        tracker._on_caret_moved(mock_event)

        self.assertEqual(tracker._x, 100)
        self.assertEqual(tracker._y, 200)

    def test_caret_tracker_on_caret_moved_int_min(self) -> None:
        tracker = CaretTracker(self.mock_logger)
        mock_event = Mock()
        mock_source = Mock()
        mock_source.is_text.return_value = True
        mock_source.get_caret_offset.return_value = 5
        mock_source.get_character_count.return_value = 10
        mock_rect = Mock()
        mock_rect.x = -2147483648
        mock_rect.y = 100
        mock_rect.width = 10
        mock_rect.height = 15
        mock_source.get_character_extents.return_value = mock_rect
        mock_event.source = mock_source

        tracker._on_caret_moved(mock_event)

        self.assertIsNone(tracker._x)
        self.assertIsNone(tracker._y)

    def test_caret_tracker_on_caret_moved_exception(self) -> None:
        tracker = CaretTracker(self.mock_logger)
        mock_event = Mock()
        mock_source = Mock()
        mock_source.is_text.side_effect = Exception("test exception")
        mock_event.source = mock_source

        tracker._on_caret_moved(mock_event)

        self.mock_logger.log.assert_called()
        self.mock_logger.log.assert_any_call(unittest.mock.ANY)

    def test_caret_tracker_on_caret_moved_offset_equal_char_count(self) -> None:
        tracker = CaretTracker(self.mock_logger)
        mock_event = Mock()
        mock_source = Mock()
        mock_source.is_text.return_value = True
        mock_source.get_caret_offset.return_value = 10
        mock_source.get_character_count.return_value = 10
        mock_rect = Mock()
        mock_rect.x = 100
        mock_rect.y = 200
        mock_rect.width = 10
        mock_rect.height = 15
        mock_source.get_character_extents.return_value = mock_rect
        mock_event.source = mock_source

        tracker._on_caret_moved(mock_event)

        self.assertEqual(tracker._x, 100)
        self.assertEqual(tracker._y, 200)

    def test_caret_tracker_on_focus_changed_offset_equal_char_count(self) -> None:
        tracker = CaretTracker(self.mock_logger)
        mock_event = Mock()
        mock_event.detail1 = True
        mock_source = Mock()
        mock_source.is_text.return_value = True
        mock_source.get_caret_offset.return_value = 10
        mock_source.get_character_count.return_value = 10
        mock_rect = Mock()
        mock_rect.x = 100
        mock_rect.y = 200
        mock_rect.width = 10
        mock_rect.height = 15
        mock_source.get_character_extents.return_value = mock_rect
        mock_event.source = mock_source

        tracker._on_focus_changed(mock_event)

        self.assertEqual(tracker._x, 110)
        self.assertEqual(tracker._y, 200)

    def test_caret_tracker_on_focus_changed_int_min(self) -> None:
        tracker = CaretTracker(self.mock_logger)
        mock_event = Mock()
        mock_event.detail1 = True
        mock_source = Mock()
        mock_source.is_text.return_value = True
        mock_source.get_caret_offset.return_value = 5
        mock_source.get_character_count.return_value = 10
        mock_rect = Mock()
        mock_rect.x = 100
        mock_rect.y = -2147483648
        mock_rect.width = 10
        mock_rect.height = 15
        mock_source.get_character_extents.return_value = mock_rect
        mock_event.source = mock_source

        tracker._on_focus_changed(mock_event)

        self.assertIsNone(tracker._x)
        self.assertIsNone(tracker._y)

    def test_caret_tracker_on_focus_changed_negative_offset(self) -> None:
        tracker = CaretTracker(self.mock_logger)
        tracker._x = 100
        tracker._y = 200
        mock_event = Mock()
        mock_event.detail1 = True
        mock_source = Mock()
        mock_source.is_text.return_value = True
        mock_source.get_caret_offset.return_value = -1
        mock_event.source = mock_source

        tracker._on_focus_changed(mock_event)

        self.assertEqual(tracker._x, 100)
        self.assertEqual(tracker._y, 200)

    def test_caret_tracker_on_focus_changed(self) -> None:
        tracker = CaretTracker(self.mock_logger)
        mock_event = Mock()
        mock_event.detail1 = True
        mock_source = Mock()
        mock_source.is_text.return_value = True
        mock_source.get_caret_offset.return_value = 5
        mock_source.get_character_count.return_value = 10
        mock_rect = Mock()
        mock_rect.x = 100
        mock_rect.y = 200
        mock_rect.width = 10
        mock_rect.height = 15
        mock_source.get_character_extents.return_value = mock_rect
        mock_event.source = mock_source

        tracker._on_focus_changed(mock_event)

        self.assertEqual(tracker._x, 110)
        self.assertEqual(tracker._y, 200)

    def test_caret_tracker_on_focus_changed_not_focused(self) -> None:
        tracker = CaretTracker(self.mock_logger)
        tracker._x = 100
        tracker._y = 200
        mock_event = Mock()
        mock_event.detail1 = False
        mock_source = Mock()
        mock_event.source = mock_source

        tracker._on_focus_changed(mock_event)

        self.assertEqual(tracker._x, 100)
        self.assertEqual(tracker._y, 200)

    def test_caret_tracker_on_focus_changed_not_text(self) -> None:
        tracker = CaretTracker(self.mock_logger)
        tracker._x = 100
        tracker._y = 200
        mock_event = Mock()
        mock_event.detail1 = True
        mock_source = Mock()
        mock_source.is_text.return_value = False
        mock_event.source = mock_source

        tracker._on_focus_changed(mock_event)

        self.assertEqual(tracker._x, 100)
        self.assertEqual(tracker._y, 200)

    def test_caret_tracker_on_focus_changed_exception(self) -> None:
        tracker = CaretTracker(self.mock_logger)
        mock_event = Mock()
        mock_event.detail1 = True
        mock_source = Mock()
        mock_source.is_text.return_value = True
        mock_source.get_caret_offset.side_effect = Exception("test exception")
        mock_event.source = mock_source

        tracker._on_focus_changed(mock_event)

        self.mock_logger.log.assert_called()
        self.mock_logger.log.assert_any_call(unittest.mock.ANY)


class CursorIndicatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_logger = Mock()
        self.mock_libx11 = Mock()
        self.mock_libx11.XDefaultScreen.return_value = 0
        self.mock_libx11.XDefaultVisual.return_value = 0x1234
        self.mock_libx11.XDefaultColormap.return_value = 0x5678
        self.mock_libx11.XDefaultRootWindow.return_value = 0x100
        self.mock_libx11.XCreateWindow.return_value = 0x200
        self.mock_libx11.XCreateGC.return_value = 0x300
        self.mock_libx11.XCreatePixmap.return_value = 0x400
        self.mock_libx11.XInternAtom.return_value = 1
        self.mock_libx11.XQueryPointer.return_value = 1
        self.mock_display = 0xDEADBEEF
        self.mock_root = 0xCAFE

    @patch('ctypes.cdll.LoadLibrary')
    def test_cursor_indicator_init(self, mock_load_library) -> None:
        mock_libxext = Mock()
        mock_libxrender = Mock()
        mock_load_library.side_effect = [mock_libxext, mock_libxrender]
        mock_libxrender.XRenderCreatePicture.return_value = 0x500

        indicator = CursorIndicator(
            self.mock_libx11,
            self.mock_display,
            self.mock_root,
            self.mock_logger
        )

        self.assertEqual(indicator.libx11, self.mock_libx11)
        self.assertEqual(indicator.display, self.mock_display)
        self.assertEqual(indicator.root, self.mock_root)
        self.assertEqual(indicator.logger, self.mock_logger)
        self.assertEqual(indicator._window, 0x200)
        self.assertIsNotNone(indicator._window_gc)

    @patch('ctypes.cdll.LoadLibrary')
    def test_cursor_indicator_show_no_caret(self, mock_load_library) -> None:
        mock_libxext = Mock()
        mock_libxrender = Mock()
        mock_load_library.side_effect = [mock_libxext, mock_libxrender]
        mock_libxrender.XRenderCreatePicture.return_value = 0x500

        indicator = CursorIndicator(
            self.mock_libx11,
            self.mock_display,
            self.mock_root,
            self.mock_logger
        )

        indicator.show()

        self.mock_libx11.XQueryPointer.assert_called_once()
        self.mock_libx11.XMoveWindow.assert_called_once()
        self.mock_libx11.XMapWindow.assert_called_once()

    @patch('ctypes.cdll.LoadLibrary')
    def test_cursor_indicator_show_with_caret(self, mock_load_library) -> None:
        mock_libxext = Mock()
        mock_libxrender = Mock()
        mock_load_library.side_effect = [mock_libxext, mock_libxrender]
        mock_libxrender.XRenderCreatePicture.return_value = 0x500

        mock_caret_tracker = Mock()
        mock_caret_tracker.get_position.return_value = (100, 200)

        indicator = CursorIndicator(
            self.mock_libx11,
            self.mock_display,
            self.mock_root,
            self.mock_logger,
            caret_tracker=mock_caret_tracker
        )

        indicator.show()

        mock_caret_tracker.get_position.assert_called_once()
        self.mock_libx11.XQueryPointer.assert_not_called()
        self.assertEqual(indicator._pos_x, 93)
        self.assertEqual(indicator._pos_y, 176)
        self.mock_libx11.XMoveWindow.assert_called_once()
        self.mock_libx11.XMapWindow.assert_called_once()

    @patch('ctypes.cdll.LoadLibrary')
    def test_cursor_indicator_show_no_window(self, mock_load_library) -> None:
        mock_libxext = Mock()
        mock_libxrender = Mock()
        mock_load_library.side_effect = [mock_libxext, mock_libxrender]

        self.mock_libx11.XCreateWindow.return_value = 0

        indicator = CursorIndicator(
            self.mock_libx11,
            self.mock_display,
            self.mock_root,
            self.mock_logger
        )

        indicator.show()

        self.mock_libx11.XMoveWindow.assert_not_called()
        self.mock_libx11.XMapWindow.assert_not_called()

    @patch('ctypes.cdll.LoadLibrary')
    def test_cursor_indicator_hide(self, mock_load_library) -> None:
        mock_libxext = Mock()
        mock_libxrender = Mock()
        mock_load_library.side_effect = [mock_libxext, mock_libxrender]
        mock_libxrender.XRenderCreatePicture.return_value = 0x500

        indicator = CursorIndicator(
            self.mock_libx11,
            self.mock_display,
            self.mock_root,
            self.mock_logger
        )

        indicator.hide()

        self.mock_libx11.XUnmapWindow.assert_called_once()
        self.mock_libx11.XSync.assert_called_once()
        self.assertFalse(indicator._visible)

    @patch('ctypes.cdll.LoadLibrary')
    def test_cursor_indicator_hide_no_window(self, mock_load_library) -> None:
        mock_libxext = Mock()
        mock_libxrender = Mock()
        mock_load_library.side_effect = [mock_libxext, mock_libxrender]

        self.mock_libx11.XCreateWindow.return_value = 0

        indicator = CursorIndicator(
            self.mock_libx11,
            self.mock_display,
            self.mock_root,
            self.mock_logger
        )

        indicator.hide()

        self.mock_libx11.XUnmapWindow.assert_not_called()

    @patch('ctypes.cdll.LoadLibrary')
    def test_cursor_indicator_destroy(self, mock_load_library) -> None:
        mock_libxext = Mock()
        mock_libxrender = Mock()
        mock_load_library.side_effect = [mock_libxext, mock_libxrender]
        mock_libxrender.XRenderCreatePicture.return_value = 0x500

        indicator = CursorIndicator(
            self.mock_libx11,
            self.mock_display,
            self.mock_root,
            self.mock_logger
        )

        indicator.destroy()

        self.mock_libx11.XFreeGC.assert_called()
        self.mock_libx11.XFreePixmap.assert_called()
        self.mock_libx11.XUnmapWindow.assert_called_once()
        self.mock_libx11.XDestroyWindow.assert_called_once()
        self.assertEqual(indicator._window, 0)
        self.assertIsNone(indicator._window_gc)

    @patch('ctypes.cdll.LoadLibrary')
    def test_cursor_indicator_tick(self, mock_load_library) -> None:
        mock_libxext = Mock()
        mock_libxrender = Mock()
        mock_load_library.side_effect = [mock_libxext, mock_libxrender]
        mock_libxrender.XRenderCreatePicture.return_value = 0x500

        indicator = CursorIndicator(
            self.mock_libx11,
            self.mock_display,
            self.mock_root,
            self.mock_logger
        )

        indicator.tick()

        self.assertTrue(True)

    @patch('ctypes.cdll.LoadLibrary')
    def test_cursor_indicator_init_no_libxext(self, mock_load_library) -> None:
        mock_libxext = Mock()
        mock_libxrender = Mock()
        mock_load_library.side_effect = [OSError("not found"), mock_libxrender]
        mock_libxrender.XRenderCreatePicture.return_value = 0x500

        indicator = CursorIndicator(
            self.mock_libx11,
            self.mock_display,
            self.mock_root,
            self.mock_logger
        )

        self.mock_logger.log.assert_any_call(
            unittest.mock.ANY
        )

    @patch('ctypes.cdll.LoadLibrary')
    def test_cursor_indicator_init_no_libxrender(self, mock_load_library) -> None:
        mock_libxext = Mock()
        mock_libxrender = Mock()
        mock_load_library.side_effect = [mock_libxext, OSError("not found")]

        indicator = CursorIndicator(
            self.mock_libx11,
            self.mock_display,
            self.mock_root,
            self.mock_logger
        )

        self.mock_logger.log.assert_any_call(
            unittest.mock.ANY
        )

    @patch('ctypes.cdll.LoadLibrary')
    def test_cursor_indicator_show_caret_none(self, mock_load_library) -> None:
        mock_libxext = Mock()
        mock_libxrender = Mock()
        mock_load_library.side_effect = [mock_libxext, mock_libxrender]
        mock_libxrender.XRenderCreatePicture.return_value = 0x500

        mock_caret_tracker = Mock()
        mock_caret_tracker.get_position.return_value = None

        indicator = CursorIndicator(
            self.mock_libx11,
            self.mock_display,
            self.mock_root,
            self.mock_logger,
            caret_tracker=mock_caret_tracker
        )

        indicator.show()

        self.mock_libx11.XQueryPointer.assert_called_once()

    @patch('ctypes.cdll.LoadLibrary')
    def test_cursor_indicator_show_query_fails(self, mock_load_library) -> None:
        mock_libxext = Mock()
        mock_libxrender = Mock()
        mock_load_library.side_effect = [mock_libxext, mock_libxrender]
        mock_libxrender.XRenderCreatePicture.return_value = 0x500

        self.mock_libx11.XQueryPointer.return_value = 0

        indicator = CursorIndicator(
            self.mock_libx11,
            self.mock_display,
            self.mock_root,
            self.mock_logger
        )

        indicator.show()

        self.mock_libx11.XMapWindow.assert_called_once()

    @patch('ctypes.cdll.LoadLibrary')
    def test_cursor_indicator_init_no_argb_visual(self, mock_load_library) -> None:
        mock_libxext = Mock()
        mock_libxrender = Mock()
        mock_load_library.side_effect = [mock_libxext, mock_libxrender]
        mock_libxrender.XRenderCreatePicture.return_value = 0x500
        mock_libxrender.XRenderFindVisualFormat.return_value = None

        indicator = CursorIndicator(
            self.mock_libx11,
            self.mock_display,
            self.mock_root,
            self.mock_logger
        )

        self.assertEqual(indicator._picture, 0)

    @patch('ctypes.cdll.LoadLibrary')
    def test_cursor_indicator_create_circle_shape_no_pixmap(self, mock_load_library) -> None:
        mock_libxext = Mock()
        mock_libxrender = Mock()
        mock_load_library.side_effect = [mock_libxext, mock_libxrender]
        mock_libxrender.XRenderCreatePicture.return_value = 0x500
        self.mock_libx11.XCreatePixmap.return_value = 0

        indicator = CursorIndicator(
            self.mock_libx11,
            self.mock_display,
            self.mock_root,
            self.mock_logger
        )

        self.assertEqual(indicator._shape_pixmap, 0)

    @patch('ctypes.cdll.LoadLibrary')
    def test_cursor_indicator_create_circle_shape_no_gc(self, mock_load_library) -> None:
        mock_libxext = Mock()
        mock_libxrender = Mock()
        mock_load_library.side_effect = [mock_libxext, mock_libxrender]
        mock_libxrender.XRenderCreatePicture.return_value = 0x500
        self.mock_libx11.XCreatePixmap.return_value = 0x400
        self.mock_libx11.XCreateGC.return_value = 0

        indicator = CursorIndicator(
            self.mock_libx11,
            self.mock_display,
            self.mock_root,
            self.mock_logger
        )

        self.assertEqual(indicator._shape_pixmap, 0)
        self.mock_libx11.XFreePixmap.assert_called_once()

    @patch('ctypes.cdll.LoadLibrary')
    def test_cursor_indicator_draw_static_indicator_fallback(self, mock_load_library) -> None:
        mock_libxext = Mock()
        mock_libxrender = Mock()
        mock_load_library.side_effect = [mock_libxext, mock_libxrender]
        mock_libxrender.XRenderCreatePicture.return_value = 0x500

        indicator = CursorIndicator(
            self.mock_libx11,
            self.mock_display,
            self.mock_root,
            self.mock_logger
        )

        indicator._picture = 0
        indicator._window_gc = self.mock_libx11.XCreateGC.return_value

        indicator._draw_static_indicator()

        self.mock_libx11.XFillArc.assert_called()
        self.mock_libx11.XFillRectangle.assert_called()
        self.mock_libx11.XSetForeground.assert_called()

    @patch('ctypes.cdll.LoadLibrary')
    def test_cursor_indicator_draw_fallback_no_gc(self, mock_load_library) -> None:
        mock_libxext = Mock()
        mock_libxrender = Mock()
        mock_load_library.side_effect = [mock_libxext, mock_libxrender]
        mock_libxrender.XRenderCreatePicture.return_value = 0x500

        indicator = CursorIndicator(
            self.mock_libx11,
            self.mock_display,
            self.mock_root,
            self.mock_logger
        )

        indicator._window_gc = None
        self.mock_libx11.XFillArc.reset_mock()

        indicator._draw_fallback()

        self.mock_libx11.XFillArc.assert_not_called()

    @patch('ctypes.cdll.LoadLibrary')
    def test_cursor_indicator_no_render_extension(self, mock_load_library) -> None:
        mock_libxext = Mock()
        mock_load_library.side_effect = [OSError("not found"), OSError("not found")]

        indicator = CursorIndicator(
            self.mock_libx11,
            self.mock_display,
            self.mock_root,
            self.mock_logger
        )

        self.assertEqual(indicator._picture, 0)
        self.assertEqual(indicator._ext_render, False)
        self.assertEqual(indicator._ext_shape, False)

    @patch('ctypes.cdll.LoadLibrary')
    def test_cursor_indicator_argb_visual_not_found(self, mock_load_library) -> None:
        mock_libxext = Mock()
        mock_libxrender = Mock()
        mock_load_library.side_effect = [mock_libxext, mock_libxrender]
        mock_libxrender.XRenderCreatePicture.return_value = 0x500
        mock_libxrender.XRenderFindVisualFormat.return_value = None

        indicator = CursorIndicator(
            self.mock_libx11,
            self.mock_display,
            self.mock_root,
            self.mock_logger
        )

        self.mock_logger.log.assert_any_call(unittest.mock.ANY)

    @patch('ctypes.cdll.LoadLibrary')
    def test_cursor_indicator_default_24bit_visual(self, mock_load_library) -> None:
        mock_libxext = Mock()
        mock_libxrender = Mock()
        mock_load_library.side_effect = [mock_libxext, mock_libxrender]
        mock_libxrender.XRenderFindVisualFormat.return_value = None
        mock_libxrender.XRenderCreatePicture.return_value = 0x500

        indicator = CursorIndicator(
            self.mock_libx11,
            self.mock_display,
            self.mock_root,
            self.mock_logger
        )

        self.assertEqual(indicator._argb_visual, None)


if __name__ == "__main__":
    unittest.main()
