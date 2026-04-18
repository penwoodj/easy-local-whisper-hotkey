import unittest
from unittest.mock import Mock, patch

from whisper_hotkey.postprocessor import (
    PostProcessor,
    PostProcessMode,
    PostProcessTrigger,
)


class PostProcessorTests(unittest.TestCase):
    def test_mode_enum_values(self) -> None:
        self.assertEqual(PostProcessMode.OFF.value, "off")
        self.assertEqual(PostProcessMode.LIGHT.value, "light")
        self.assertEqual(PostProcessMode.AGGRESSIVE.value, "aggressive")
        self.assertEqual(PostProcessMode.AGENTIC.value, "agentic")
        self.assertEqual(PostProcessMode.WRITING.value, "writing")
        self.assertEqual(PostProcessMode.CODE.value, "code")
        self.assertEqual(PostProcessMode.STRUCTURE.value, "structure")
        self.assertEqual(PostProcessMode.PERSONA.value, "persona")
        self.assertEqual(PostProcessMode.CLARITY.value, "clarity")

    def test_trigger_enum_values(self) -> None:
        self.assertEqual(PostProcessTrigger.ALWAYS.value, "always")
        self.assertEqual(PostProcessTrigger.MANUAL.value, "manual")
        self.assertEqual(PostProcessTrigger.AUTO_LONG.value, "auto-long")
        self.assertEqual(PostProcessTrigger.PREVIEW.value, "preview")

    def test_should_process_always_trigger(self) -> None:
        pp = PostProcessor(
            mode=PostProcessMode.LIGHT,
            trigger=PostProcessTrigger.ALWAYS,
        )
        self.assertFalse(pp.should_process(""))
        self.assertTrue(pp.should_process("short"))
        self.assertTrue(pp.should_process("longer text with many words"))

    def test_should_process_manual_trigger(self) -> None:
        pp = PostProcessor(
            mode=PostProcessMode.LIGHT,
            trigger=PostProcessTrigger.MANUAL,
        )
        self.assertFalse(pp.should_process(""))
        self.assertFalse(pp.should_process("any text"))
        self.assertFalse(pp.should_process("longer text with many words"))

    def test_should_process_auto_long_trigger_short_text(self) -> None:
        pp = PostProcessor(
            mode=PostProcessMode.LIGHT,
            trigger=PostProcessTrigger.AUTO_LONG,
        )
        short_text = "This is a short text with fewer than fifty words"
        word_count = len(short_text.split())
        self.assertLess(word_count, 50)
        self.assertFalse(pp.should_process(short_text))

    def test_should_process_auto_long_trigger_long_text(self) -> None:
        pp = PostProcessor(
            mode=PostProcessMode.LIGHT,
            trigger=PostProcessTrigger.AUTO_LONG,
        )
        long_text = "word " * 51
        word_count = len(long_text.split())
        self.assertGreater(word_count, 50)
        self.assertTrue(pp.should_process(long_text))

    def test_should_process_preview_trigger(self) -> None:
        pp = PostProcessor(
            mode=PostProcessMode.LIGHT,
            trigger=PostProcessTrigger.PREVIEW,
        )
        self.assertFalse(pp.should_process(""))
        self.assertFalse(pp.should_process("any text"))

    def test_process_off_mode(self) -> None:
        pp = PostProcessor(
            mode=PostProcessMode.OFF,
            trigger=PostProcessTrigger.ALWAYS,
        )
        text = "This is a test"
        result = pp.process(text)
        self.assertEqual(result, text)

    def test_process_light_mode_import_error(self) -> None:
        pp = PostProcessor(
            mode=PostProcessMode.LIGHT,
            trigger=PostProcessTrigger.ALWAYS,
        )
        text = "This is a test"
        result = pp.process(text)

        self.assertEqual(result, text)

    def test_process_aggressive_mode_import_error(self) -> None:
        pp = PostProcessor(
            mode=PostProcessMode.AGGRESSIVE,
            trigger=PostProcessTrigger.ALWAYS,
        )
        text = "This is a test"
        result = pp.process(text)

        self.assertEqual(result, text)

    @patch("whisper_hotkey.postprocessor.os.environ.get")
    def test_process_agentic_mode_no_api_key(self, mock_getenv) -> None:
        mock_getenv.return_value = None

        pp = PostProcessor(
            mode=PostProcessMode.AGENTIC,
            trigger=PostProcessTrigger.ALWAYS,
        )
        text = "this is a test"
        result = pp.process(text)

        self.assertEqual(result, text)

    @patch("whisper_hotkey.postprocessor.os.environ.get")
    def test_process_agentic_mode_with_api_key(self, mock_getenv) -> None:
        mock_getenv.return_value = "test-key"

        pp = PostProcessor(
            mode=PostProcessMode.AGENTIC,
            trigger=PostProcessTrigger.ALWAYS,
        )
        text = "this is a test"
        result = pp.process(text)

        self.assertEqual(result, text)

    def test_process_placeholder_modes_fallback_to_light(self) -> None:
        placeholder_modes = [
            PostProcessMode.WRITING,
            PostProcessMode.CODE,
            PostProcessMode.STRUCTURE,
            PostProcessMode.PERSONA,
            PostProcessMode.CLARITY,
        ]

        for mode in placeholder_modes:
            with self.subTest(mode=mode):
                pp = PostProcessor(
                    mode=mode,
                    trigger=PostProcessTrigger.ALWAYS,
                )
                text = "this is a test"
                result = pp.process(text)

                self.assertEqual(result, text)

    def test_find_qwen_model_method_exists(self) -> None:
        pp = PostProcessor(
            mode=PostProcessMode.AGGRESSIVE,
            trigger=PostProcessTrigger.ALWAYS,
        )
        self.assertTrue(hasattr(pp, "_find_qwen_model"))

    def test_process_empty_text(self) -> None:
        pp = PostProcessor(
            mode=PostProcessMode.LIGHT,
            trigger=PostProcessTrigger.ALWAYS,
        )
        text = ""
        result = pp.process(text)
        self.assertEqual(result, text)

    def test_process_unicode_text(self) -> None:
        pp = PostProcessor(
            mode=PostProcessMode.LIGHT,
            trigger=PostProcessTrigger.ALWAYS,
        )
        text = "Héllo wörld"
        result = pp.process(text)
        self.assertEqual(result, text)


if __name__ == "__main__":
    unittest.main()
