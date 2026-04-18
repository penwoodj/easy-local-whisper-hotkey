import unittest
from unittest.mock import Mock

from whisper_hotkey import app


class SessionTrackingTests(unittest.TestCase):
    def test_on_text_typed_accumulates_text(self) -> None:
        mock_logger = Mock()
        mock_source = "test-source"
        mock_whisper_cli = "/path/to/whisper"
        mock_model = "/path/to/model"

        daemon = app.X11HotkeyDaemon(
            source=mock_source,
            whisper_cli=mock_whisper_cli,
            model=mock_model,
            language="en",
            chunk_seconds=3.5,
            overlap_seconds=0.8,
            type_delay_ms=1,
            logger=mock_logger,
        )
        daemon._postprocessing_enabled = True

        daemon._on_text_typed("Hello ")
        self.assertEqual(daemon._session_text, "  Hello ")

        daemon._on_text_typed("world")
        self.assertEqual(daemon._session_text, "  Hello   world")

        daemon._on_text_typed("!")
        self.assertEqual(daemon._session_text, "  Hello   world  !")

    def test_reset_session_text_clears_accumulated_text(self) -> None:
        mock_logger = Mock()
        mock_source = "test-source"
        mock_whisper_cli = "/path/to/whisper"
        mock_model = "/path/to/model"

        daemon = app.X11HotkeyDaemon(
            source=mock_source,
            whisper_cli=mock_whisper_cli,
            model=mock_model,
            language="en",
            chunk_seconds=3.5,
            overlap_seconds=0.8,
            type_delay_ms=1,
            logger=mock_logger,
        )
        daemon._postprocessing_enabled = True

        daemon._on_text_typed("Some text")
        self.assertEqual(daemon._session_text, "  Some text")

        daemon._reset_session_text()
        self.assertEqual(daemon._session_text, "")

    def test_on_text_typed_empty_string(self) -> None:
        mock_logger = Mock()
        mock_source = "test-source"
        mock_whisper_cli = "/path/to/whisper"
        mock_model = "/path/to/model"

        daemon = app.X11HotkeyDaemon(
            source=mock_source,
            whisper_cli=mock_whisper_cli,
            model=mock_model,
            language="en",
            chunk_seconds=3.5,
            overlap_seconds=0.8,
            type_delay_ms=1,
            logger=mock_logger,
        )
        daemon._postprocessing_enabled = True

        daemon._on_text_typed("")
        self.assertEqual(daemon._session_text, "  ")

    def test_on_text_typed_unicode(self) -> None:
        mock_logger = Mock()
        mock_source = "test-source"
        mock_whisper_cli = "/path/to/whisper"
        mock_model = "/path/to/model"

        daemon = app.X11HotkeyDaemon(
            source=mock_source,
            whisper_cli=mock_whisper_cli,
            model=mock_model,
            language="en",
            chunk_seconds=3.5,
            overlap_seconds=0.8,
            type_delay_ms=1,
            logger=mock_logger,
        )
        daemon._postprocessing_enabled = True

        daemon._on_text_typed("Héllo ")
        daemon._on_text_typed("wörld")
        self.assertEqual(daemon._session_text, "  Héllo   wörld")

    def test_run_postprocessing_enabled_flag_required(self) -> None:
        mock_logger = Mock()
        mock_source = "test-source"
        mock_whisper_cli = "/path/to/whisper"
        mock_model = "/path/to/model"

        daemon = app.X11HotkeyDaemon(
            source=mock_source,
            whisper_cli=mock_whisper_cli,
            model=mock_model,
            language="en",
            chunk_seconds=3.5,
            overlap_seconds=0.8,
            type_delay_ms=1,
            logger=mock_logger,
        )

        daemon._session_text = "Some text"
        daemon._run_postprocessing()

        self.assertFalse(mock_logger.log.called)

    def test_session_text_empty_on_initialization(self) -> None:
        mock_logger = Mock()
        mock_source = "test-source"
        mock_whisper_cli = "/path/to/whisper"
        mock_model = "/path/to/model"

        daemon = app.X11HotkeyDaemon(
            source=mock_source,
            whisper_cli=mock_whisper_cli,
            model=mock_model,
            language="en",
            chunk_seconds=3.5,
            overlap_seconds=0.8,
            type_delay_ms=1,
            logger=mock_logger,
        )

        self.assertEqual(daemon._session_text, "")


class FocusOutDetectionTests(unittest.TestCase):
    def test_focus_out_constant_defined(self) -> None:
        self.assertTrue(hasattr(app, "FOCUS_OUT"))
        self.assertEqual(app.FOCUS_OUT, 10)


if __name__ == "__main__":
    unittest.main()
