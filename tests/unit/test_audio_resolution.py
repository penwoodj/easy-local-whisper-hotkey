import unittest
from unittest.mock import patch

from whisper_hotkey import app


class AudioResolutionTests(unittest.TestCase):
    @patch("whisper_hotkey.app.list_sources", return_value=["mic-a", "mic-b"])
    def test_explicit_source_wins(self, _list_sources) -> None:
        source = app.resolve_audio_source("mic-b", ["mic-a"], None)
        self.assertEqual(source, "mic-b")

    @patch("whisper_hotkey.app.get_default_source", return_value="")
    @patch("whisper_hotkey.app.list_sources", return_value=["mic-b", "mic-a"])
    def test_preferred_sources_choose_first_match(self, _list_sources, _default_source) -> None:
        source = app.resolve_audio_source("", ["missing", "mic-a", "mic-b"], None)
        self.assertEqual(source, "mic-a")

    @patch("whisper_hotkey.app.get_default_source", return_value="desktop-default")
    @patch("whisper_hotkey.app.list_sources", return_value=["desktop-default", "mic-b"])
    def test_falls_back_to_desktop_default(self, _list_sources, _default_source) -> None:
        source = app.resolve_audio_source("", [], None)
        self.assertEqual(source, "desktop-default")

    @patch("whisper_hotkey.app.get_default_source", return_value="")
    @patch("whisper_hotkey.app.list_sources", return_value=["speaker.monitor", "mic-b"])
    def test_skips_monitor_sources_for_capture_fallback(self, _list_sources, _default_source) -> None:
        source = app.resolve_audio_source("", [], None)
        self.assertEqual(source, "mic-b")


if __name__ == "__main__":
    unittest.main()
