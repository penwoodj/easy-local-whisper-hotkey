import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

from whisper_hotkey import app


class ComputeAppendTextExtendedTests(unittest.TestCase):
    def test_compute_append_text_empty_history(self) -> None:
        history = []
        new_text = "hello world"
        result = app.compute_append_text(history, new_text)
        self.assertEqual(result, "hello world")

    def test_compute_append_text_empty_new_text(self) -> None:
        history = ["hello", "world"]
        new_text = ""
        result = app.compute_append_text(history, new_text)
        self.assertEqual(result, "")

    def test_compute_append_text_single_word_history(self) -> None:
        history = ["hello"]
        new_text = "hello world"
        result = app.compute_append_text(history, new_text)
        self.assertEqual(result, "world")

    def test_compute_append_text_history_exactly_matches_new_text_start(self) -> None:
        history = ["hello", "world"]
        new_text = "hello world again"
        result = app.compute_append_text(history, new_text)
        self.assertEqual(result, "again")

    def test_compute_append_text_very_long_history_truncated(self) -> None:
        history = [f"word{i}" for i in range(40)]
        new_text = "word38 word39 new words here"
        result = app.compute_append_text(history, new_text)
        self.assertEqual(result, "new words here")

    def test_compute_append_text_fuzzy_overlap_sequence_matcher(self) -> None:
        history = ["testing", "is", "fun"]
        new_text = "testing is fun again"
        result = app.compute_append_text(history, new_text)
        self.assertEqual(result, "again")

    def test_compute_append_text_fuzzy_overlap_below_threshold(self) -> None:
        history = ["hello", "world"]
        new_text = "helo world test"
        result = app.compute_append_text(history, new_text)
        self.assertEqual(result, "helo world test")

    def test_compute_append_text_case_insensitive_fuzzy(self) -> None:
        history = ["Hello", "World"]
        new_text = "hello world testing"
        result = app.compute_append_text(history, new_text)
        self.assertEqual(result, "testing")

    def test_compute_append_text_no_overlap(self) -> None:
        history = ["first", "second"]
        new_text = "completely different text"
        result = app.compute_append_text(history, new_text)
        self.assertEqual(result, "completely different text")

    def test_compute_append_text_partial_overlap(self) -> None:
        history = ["the", "quick", "brown", "fox"]
        new_text = "fox jumps over dog"
        result = app.compute_append_text(history, new_text)
        self.assertEqual(result, "jumps over dog")


class DeduplicateFlushTextTests(unittest.TestCase):
    def test_deduplicate_flush_text_short_text_returns_as_is(self) -> None:
        text = "hello world"
        result = app._deduplicate_flush_text(text)
        self.assertEqual(result, "hello world")

    def test_deduplicate_flush_text_three_words_returns_as_is(self) -> None:
        text = "one two three"
        result = app._deduplicate_flush_text(text)
        self.assertEqual(result, "one two three")

    def test_deduplicate_flush_text_exact_duplicate_phrases_four_words(self) -> None:
        text = "hello world test again hello world test again"
        result = app._deduplicate_flush_text(text)
        self.assertEqual(result, "hello world test again")

    def test_deduplicate_flush_text_fuzzy_duplicate_phrases_four_words(self) -> None:
        text = "hello world test again hello world test again end"
        result = app._deduplicate_flush_text(text)
        self.assertEqual(result, "hello world test again end")

    def test_deduplicate_flush_text_multiple_duplicate_pairs_different_positions(self) -> None:
        text = "a b c d e a b c d e f g h f g h"
        result = app._deduplicate_flush_text(text)
        self.assertEqual(result, "a b c d e f g h")

    def test_deduplicate_flush_text_clean_text_no_duplicates(self) -> None:
        text = "this is a clean sentence with no repeated phrases at all"
        result = app._deduplicate_flush_text(text)
        self.assertEqual(result, text)

    def test_deduplicate_flush_text_three_consecutive_repetitions_four_words(self) -> None:
        text = "test phrase one two test phrase one two test phrase one two"
        result = app._deduplicate_flush_text(text)
        self.assertEqual(result, "test phrase one two")

    def test_deduplicate_flush_text_long_duplicate_phrase(self) -> None:
        text = "the quick brown fox jumps over the quick brown fox jumps over dog"
        result = app._deduplicate_flush_text(text)
        self.assertEqual(result, "the quick brown fox jumps over dog")

    def test_deduplicate_flush_text_multiple_iterations_needed(self) -> None:
        text = "a b c d a b c d e f g h e f g h"
        result = app._deduplicate_flush_text(text)
        self.assertEqual(result, "a b c d e f g h")

    def test_deduplicate_flush_text_with_punctuation_normalization(self) -> None:
        text = "hello world test again hello world test again end"
        result = app._deduplicate_flush_text(text)
        self.assertEqual(result, "hello world test again end")


class CleanTranscriptExtendedTests(unittest.TestCase):
    def test_clean_transcript_empty_string(self) -> None:
        text = ""
        result = app.clean_transcript(text)
        self.assertEqual(result, "")

    def test_clean_transcript_all_bracket_lines_filtered(self) -> None:
        text = "[00:00:00]\n[00:00:05]\n[00:00:10]"
        result = app.clean_transcript(text)
        self.assertEqual(result, "")

    def test_clean_transcript_mixed_content_with_timestamps(self) -> None:
        text = "[00:00:00] hello\n[00:00:05] world\n[00:00:10] test"
        result = app.clean_transcript(text)
        self.assertEqual(result, "hello world test")

    def test_clean_transcript_lines_with_leading_brackets_then_text(self) -> None:
        text = "[00:00:00] First line\n[00:00:05] Second line\nThird line"
        result = app.clean_transcript(text)
        self.assertEqual(result, "First line Second line Third line")

    def test_clean_transcript_multiple_consecutive_blank_lines(self) -> None:
        text = "hello\n\n\n\n\nworld\n\n\n\ntest"
        result = app.clean_transcript(text)
        self.assertEqual(result, "hello world test")

    def test_clean_transcript_lines_with_brackets_only(self) -> None:
        text = "[Music]\n[Applause]\nhello world"
        result = app.clean_transcript(text)
        self.assertEqual(result, "hello world")

    def test_clean_transcript_lines_only_spaces(self) -> None:
        text = "hello\n   \n\n  \nworld"
        result = app.clean_transcript(text)
        self.assertEqual(result, "hello world")

    def test_clean_transcript_bracket_not_at_start(self) -> None:
        text = "hello [world] test"
        result = app.clean_transcript(text)
        self.assertEqual(result, "hello [world] test")


class ParseArgsTests(unittest.TestCase):
    @patch.dict('os.environ', {}, clear=True)
    def test_parse_args_default_values(self) -> None:
        args = app.parse_args([])
        # No hardcoded fallback - returns "." (empty Path) if whisper-cli not found
        self.assertEqual(args.whisper_cli, ".")
        self.assertTrue(args.model.endswith("ggml-base.en.bin"))
        self.assertEqual(args.chunk_seconds, 3.5)
        self.assertEqual(args.overlap_seconds, 0.8)
        self.assertEqual(args.type_delay_ms, 1)
        self.assertEqual(args.language, "en")
        self.assertEqual(args.suppress_regex, "[,.]")
        self.assertTrue(args.suppress_nst)
        self.assertTrue(args.smart_punctuation)
        self.assertFalse(args.symbol_words_to_symbols)
        self.assertFalse(args.direct_streaming)
        self.assertEqual(args.activation_mode, "toggle")
        self.assertTrue(args.indicator)
        self.assertFalse(args.postprocess)
        self.assertEqual(args.postprocess_mode, "off")
        self.assertEqual(args.postprocess_trigger, "manual")
        self.assertIsNone(args.test)

    @patch.dict('os.environ', {}, clear=True)
    def test_parse_args_custom_values(self) -> None:
        args = app.parse_args([
            "--whisper-cli", "/custom/whisper",
            "--model", "/custom/model.bin",
            "--source", "test-source",
            "--preferred-sources", "src1,src2",
            "--chunk-seconds", "5.0",
            "--overlap-seconds", "1.0",
            "--type-delay-ms", "10",
            "--language", "es",
            "--suppress-regex", "[.!?]",
            "--activation-mode", "hold",
        ])
        self.assertEqual(args.whisper_cli, "/custom/whisper")
        self.assertEqual(args.model, "/custom/model.bin")
        self.assertEqual(args.source, "test-source")
        self.assertEqual(args.preferred_sources, "src1,src2")
        self.assertEqual(args.chunk_seconds, 5.0)
        self.assertEqual(args.overlap_seconds, 1.0)
        self.assertEqual(args.type_delay_ms, 10)
        self.assertEqual(args.language, "es")
        self.assertEqual(args.suppress_regex, "[.!?]")
        self.assertEqual(args.activation_mode, "hold")

    @patch.dict('os.environ', {}, clear=True)
    def test_parse_args_test_with_no_argument(self) -> None:
        args = app.parse_args(["--test"])
        self.assertEqual(args.test, "3")

    @patch.dict('os.environ', {}, clear=True)
    def test_parse_args_test_with_argument(self) -> None:
        args = app.parse_args(["--test", "10"])
        self.assertEqual(args.test, "10")

    @patch.dict('os.environ', {}, clear=True)
    def test_parse_args_activation_mode_hold(self) -> None:
        args = app.parse_args(["--activation-mode", "hold"])
        self.assertEqual(args.activation_mode, "hold")

    @patch.dict('os.environ', {}, clear=True)
    def test_parse_args_activation_mode_toggle(self) -> None:
        args = app.parse_args(["--activation-mode", "toggle"])
        self.assertEqual(args.activation_mode, "toggle")

    @patch.dict('os.environ', {}, clear=True)
    def test_parse_args_postprocess_flag(self) -> None:
        args = app.parse_args(["--postprocess"])
        self.assertTrue(args.postprocess)

    @patch.dict('os.environ', {}, clear=True)
    def test_parse_args_postprocess_mode_choices(self) -> None:
        for mode in ["off", "light", "aggressive", "agentic", "writing", "code", "structure", "persona", "clarity"]:
            args = app.parse_args(["--postprocess-mode", mode])
            self.assertEqual(args.postprocess_mode, mode)

    @patch.dict('os.environ', {}, clear=True)
    def test_parse_args_postprocess_trigger_choices(self) -> None:
        for trigger in ["always", "manual", "auto-long", "preview"]:
            args = app.parse_args(["--postprocess-trigger", trigger])
            self.assertEqual(args.postprocess_trigger, trigger)

    @patch.dict('os.environ', {'WHISPER_MODEL': '/env/model.bin'}, clear=False)
    def test_parse_args_env_variable_override(self) -> None:
        args = app.parse_args([])
        self.assertEqual(args.model, "/env/model.bin")


class ParsePreferredSourcesExtendedTests(unittest.TestCase):
    def test_parse_preferred_sources_none_returns_defaults(self) -> None:
        result = app.parse_preferred_sources(None)
        self.assertEqual(result, list(app.DEFAULT_PREFERRED_SOURCES))

    def test_parse_preferred_sources_empty_string_returns_defaults(self) -> None:
        result = app.parse_preferred_sources("")
        self.assertEqual(result, list(app.DEFAULT_PREFERRED_SOURCES))

    def test_parse_preferred_sources_single_source(self) -> None:
        result = app.parse_preferred_sources("mic1")
        self.assertEqual(result, ["mic1"])

    def test_parse_preferred_sources_whitespace_handling(self) -> None:
        result = app.parse_preferred_sources("  mic1  ,  mic2  ,  mic3  ")
        self.assertEqual(result, ["mic1", "mic2", "mic3"])

    def test_parse_preferred_sources_trailing_comma(self) -> None:
        result = app.parse_preferred_sources("mic1,mic2,")
        self.assertEqual(result, ["mic1", "mic2"])

    def test_parse_preferred_sources_leading_comma(self) -> None:
        result = app.parse_preferred_sources(",mic1,mic2")
        self.assertEqual(result, ["mic1", "mic2"])

    def test_parse_preferred_sources_multiple_consecutive_commas(self) -> None:
        result = app.parse_preferred_sources("mic1,,,mic2")
        self.assertEqual(result, ["mic1", "mic2"])


class RecorderExtendedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_logger = Mock()
        self.recorder = app.Recorder("test-source", self.mock_logger)

    def tearDown(self) -> None:
        if hasattr(self, 'recorder') and self.recorder.raw_path.exists():
            self.recorder.cleanup()

    def test_recorder_init_creates_temp_file(self) -> None:
        self.assertTrue(self.recorder.raw_path.exists())
        self.assertTrue(str(self.recorder.raw_path).startswith("/tmp"))
        self.assertTrue(self.recorder.raw_path.name.endswith(".s16le"))

    def test_recorder_read_segment_empty_data(self) -> None:
        result = self.recorder.read_segment(0, 100)
        self.assertEqual(result, b"")

    def test_recorder_read_segment_end_less_than_start(self) -> None:
        result = self.recorder.read_segment(100, 50)
        self.assertEqual(result, b"")

    def test_recorder_read_segment_partial_data(self) -> None:
        test_data = b"0123456789" * 100
        with self.recorder.raw_path.open("wb") as f:
            f.write(test_data)
        with self.recorder.lock:
            self.recorder.bytes_written = len(test_data)
        result = self.recorder.read_segment(0, 50)
        self.assertEqual(result, test_data[:50])

    def test_recorder_read_segment_middle_offset(self) -> None:
        test_data = b"0123456789" * 100
        with self.recorder.raw_path.open("wb") as f:
            f.write(test_data)
        with self.recorder.lock:
            self.recorder.bytes_written = len(test_data)
        result = self.recorder.read_segment(50, 100)
        self.assertEqual(result, test_data[50:100])

    def test_recorder_cleanup_removes_temp_file(self) -> None:
        self.assertTrue(self.recorder.raw_path.exists())
        self.recorder.cleanup()
        self.assertFalse(self.recorder.raw_path.exists())

    def test_recorder_cleanup_handles_missing_file(self) -> None:
        self.recorder.cleanup()
        self.assertFalse(self.recorder.raw_path.exists())
        self.recorder.cleanup()
        self.assertFalse(self.recorder.raw_path.exists())

    def test_recorder_available_returns_zero_initially(self) -> None:
        self.assertEqual(self.recorder.available(), 0)

    def test_recorder_bytes_written_tracks_correctly(self) -> None:
        test_data = b"test" * 1000
        with self.recorder.raw_path.open("wb") as f:
            f.write(test_data)
        with self.recorder.lock:
            self.recorder.bytes_written = len(test_data)
        self.assertEqual(self.recorder.available(), len(test_data))


class ResolveAudioSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_logger = Mock()

    @patch('whisper_hotkey.app.list_sources')
    def test_resolve_audio_source_preferred_found(self, mock_list_sources) -> None:
        mock_list_sources.return_value = ["source1", "source2", "source3"]
        result = app.resolve_audio_source("source2", ["source1"], self.mock_logger)
        self.assertEqual(result, "source2")
        self.mock_logger.log.assert_called_once_with("Using requested source: source2")

    @patch('whisper_hotkey.app.list_sources')
    def test_resolve_audio_source_preferred_not_found_raises_error(self, mock_list_sources) -> None:
        mock_list_sources.return_value = ["source1", "source2"]
        with self.assertRaises(RuntimeError) as context:
            app.resolve_audio_source("nonexistent", ["source1"], self.mock_logger)
        self.assertEqual(str(context.exception), "requested source not found: nonexistent")

    @patch('whisper_hotkey.app.list_sources')
    @patch('whisper_hotkey.app.get_default_source')
    def test_resolve_audio_source_no_preferred_match_falls_back_to_default(self, mock_get_default, mock_list_sources) -> None:
        mock_list_sources.return_value = ["source1", "source2", "default-source"]
        mock_get_default.return_value = "default-source"
        result = app.resolve_audio_source("", ["nonexistent"], self.mock_logger)
        self.assertEqual(result, "default-source")
        self.mock_logger.log.assert_called_once_with("Using default source: default-source")

    @patch('whisper_hotkey.app.list_sources')
    @patch('whisper_hotkey.app.get_default_source')
    def test_resolve_audio_source_default_source_is_monitor_skipped(self, mock_get_default, mock_list_sources) -> None:
        mock_list_sources.return_value = ["source1.monitor", "source1"]
        mock_get_default.return_value = "source1.monitor"
        result = app.resolve_audio_source("", ["nonexistent"], self.mock_logger)
        self.assertEqual(result, "source1")

    @patch('whisper_hotkey.app.list_sources')
    @patch('whisper_hotkey.app.get_default_source')
    def test_resolve_audio_source_all_sources_monitors_uses_first(self, mock_get_default, mock_list_sources) -> None:
        mock_list_sources.return_value = ["source1.monitor", "source2.monitor"]
        mock_get_default.return_value = ""
        result = app.resolve_audio_source("", ["nonexistent"], self.mock_logger)
        self.assertEqual(result, "source1.monitor")

    @patch('whisper_hotkey.app.list_sources')
    def test_resolve_audio_source_no_sources_raises_error(self, mock_list_sources) -> None:
        mock_list_sources.return_value = []
        with self.assertRaises(RuntimeError) as context:
            app.resolve_audio_source("", ["source1"], self.mock_logger)
        self.assertEqual(str(context.exception), "no PulseAudio/PipeWire sources found")

    @patch('whisper_hotkey.app.list_sources')
    @patch('whisper_hotkey.app.get_default_source')
    def test_resolve_audio_source_uses_preferred_in_order(self, mock_get_default, mock_list_sources) -> None:
        mock_list_sources.return_value = ["source1", "source2", "source3"]
        mock_get_default.return_value = ""
        result = app.resolve_audio_source("", ["source2", "source1"], self.mock_logger)
        self.assertEqual(result, "source2")

    @patch('whisper_hotkey.app.list_sources')
    @patch('whisper_hotkey.app.get_default_source')
    def test_resolve_audio_source_uses_first_capture_fallback(self, mock_get_default, mock_list_sources) -> None:
        mock_list_sources.return_value = ["source1", "source2.monitor", "source3"]
        mock_get_default.return_value = ""
        result = app.resolve_audio_source("", ["nonexistent"], self.mock_logger)
        self.assertEqual(result, "source1")

    @patch('whisper_hotkey.app.list_sources')
    @patch('whisper_hotkey.app.get_default_source')
    def test_resolve_audio_source_logger_none(self, mock_get_default, mock_list_sources) -> None:
        mock_list_sources.return_value = ["source1", "source2"]
        mock_get_default.return_value = "source1"
        result = app.resolve_audio_source("", ["nonexistent"], None)
        self.assertEqual(result, "source1")


if __name__ == "__main__":
    unittest.main()
