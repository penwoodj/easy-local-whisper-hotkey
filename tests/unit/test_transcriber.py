import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from whisper_hotkey import app


class TranscriberTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_logger = Mock()
        self.mock_recorder = Mock()

    def test_transcriber_init(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        self.assertEqual(transcriber.recorder, self.mock_recorder)
        self.assertEqual(transcriber.whisper_cli, Path("/path/to/whisper-cli"))
        self.assertEqual(transcriber.model, Path("/path/to/model"))
        self.assertEqual(transcriber.language, "en")
        self.assertEqual(transcriber.type_delay_ms, 1)
        self.assertEqual(transcriber.logger, self.mock_logger)
        self.assertIsNotNone(transcriber.jobs)
        self.assertEqual(len(transcriber.history_words), 0)
        self.assertEqual(len(transcriber.pending_fragments), 0)

    def test_transcriber_enqueue(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        job = app.SegmentJob(index=0, start=0, end=100, final=True)
        transcriber.enqueue(job)
        self.assertFalse(transcriber.jobs.empty())

    def test_transcriber_finish(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        transcriber.finish()
        # Get the None marker from queue
        job = transcriber.jobs.get_nowait()
        self.assertIsNone(job)
        self.assertTrue(transcriber.jobs.empty())

    def test_transcriber_flush_pending_text(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        with transcriber.pending_lock:
            transcriber.pending_fragments = ["Hello", "world"]
        with patch.object(transcriber, '_type_text') as mock_type:
            transcriber.flush_pending_text()
            mock_type.assert_called_once_with("Hello world")
        self.assertEqual(transcriber.pending_fragments, [])

    def test_transcriber_flush_pending_text_empty(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        with patch.object(transcriber, '_type_text') as mock_type:
            transcriber.flush_pending_text()
            mock_type.assert_not_called()

    def test_deduplicate_text_no_overlap(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        result = transcriber._deduplicate_text("goodbye", "hello world")
        self.assertEqual(result, "goodbye")

    def test_deduplicate_text_with_overlap(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        result = transcriber._deduplicate_text("hello world", "world goodbye")
        self.assertEqual(result, "hello world")

    def test_deduplicate_text_empty_already_typed(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        result = transcriber._deduplicate_text("hello world", "")
        self.assertEqual(result, "hello world")

    def test_deduplicate_text_case_insensitive(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        result = transcriber._deduplicate_text("HELLO", "hello world")
        self.assertEqual(result, "HELLO")

    def test_is_silence_hallucination_short_words(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        self.assertTrue(transcriber._is_silence_hallucination("uh"))
        self.assertTrue(transcriber._is_silence_hallucination("um"))
        self.assertTrue(transcriber._is_silence_hallucination("hmm"))

    def test_is_silence_hallucination_phrases(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        self.assertTrue(transcriber._is_silence_hallucination("thank you for watching"))
        self.assertTrue(transcriber._is_silence_hallucination("subscribe to my channel"))

    def test_is_silence_hallucination_normal_text(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        self.assertFalse(transcriber._is_silence_hallucination("hello world"))
        self.assertFalse(transcriber._is_silence_hallucination("this is a test"))

    def test_is_silence_hallucination_long_text(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        long_text = "word " * 10
        self.assertFalse(transcriber._is_silence_hallucination(long_text))

    def test_is_repetitive_hallucination_repetitive(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        self.assertTrue(transcriber._is_repetitive_hallucination("test test test test test test test test test test test"))

    def test_is_repetitive_hallucination_not_repetitive(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        self.assertFalse(transcriber._is_repetitive_hallucination("this is a normal sentence"))
        self.assertFalse(transcriber._is_repetitive_hallucination("hello world"))

    def test_is_repetitive_hallucination_short_text(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        self.assertFalse(transcriber._is_repetitive_hallucination("test test"))
        self.assertFalse(transcriber._is_repetitive_hallucination("short"))

    def test_fix_double_words_ellipsis(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        result = transcriber._fix_double_words("test ellipsis test")
        self.assertEqual(result, "test ellipses test")

    def test_fix_double_words_a_a(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        result = transcriber._fix_double_words("test a a test")
        self.assertEqual(result, "test a test")

    def test_fix_double_words_the(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        result = transcriber._fix_double_words("test the test")
        self.assertEqual(result, "test the test")

    def test_remove_ellipses(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        result = transcriber._remove_ellipses("hello... world...")
        self.assertEqual(result, "hello world")

    def test_remove_ellipses_many_dots(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        result = transcriber._remove_ellipses("hello........................world")
        self.assertEqual(result, "helloworld")

    def test_remove_ellipses_single_dot(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        result = transcriber._remove_ellipses("hello. world.")
        self.assertEqual(result, "hello. world.")

    def test_strip_non_speech_tokens(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        result = transcriber._strip_non_speech_tokens("hello ♪ ♫ world")
        self.assertEqual(result, "hello   world")

    def test_strip_non_speech_tokens_unicode_music(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        result = transcriber._strip_non_speech_tokens("test ♩♬♭♮♯ test")
        self.assertEqual(result, "test  test")

    def test_strip_non_speech_tokens_no_tokens(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        result = transcriber._strip_non_speech_tokens("hello world")
        self.assertEqual(result, "hello world")

    def test_strip_non_speech_tokens_only_tokens(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        result = transcriber._strip_non_speech_tokens("♪ ♫ ♩")
        self.assertEqual(result, "")

    def test_process_smart_punctuation_enabled(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
            smart_punctuation=True,
        )
        result = transcriber._process_smart_punctuation("hello comma world")
        self.assertEqual(result, "hello comma world")

    def test_process_smart_punctuation_disabled(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
            smart_punctuation=False,
        )
        result = transcriber._process_smart_punctuation("hello , world")
        self.assertEqual(result, "hello , world")

    def test_is_punctuation_word(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
        )
        self.assertTrue(transcriber._is_punctuation_word("comma"))
        self.assertTrue(transcriber._is_punctuation_word("period"))
        self.assertTrue(transcriber._is_punctuation_word("question mark"))
        self.assertFalse(transcriber._is_punctuation_word("hello"))
        self.assertFalse(transcriber._is_punctuation_word("world"))

    def test_symbol_word_to_symbol_enabled(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
            symbol_words_to_symbols=True,
        )
        result = transcriber._symbol_word_to_symbol("hello comma world")
        self.assertEqual(result, "hello, world")

    def test_symbol_word_to_symbol_disabled(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
            symbol_words_to_symbols=False,
        )
        result = transcriber._symbol_word_to_symbol("hello comma world")
        self.assertEqual(result, "hello comma world")

    def test_symbol_word_to_symbol_period(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
            symbol_words_to_symbols=True,
        )
        result = transcriber._symbol_word_to_symbol("hello period world")
        self.assertEqual(result, "hello. world")

    def test_symbol_word_to_symbol_two_words(self) -> None:
        transcriber = app.Transcriber(
            self.mock_recorder,
            Path("/path/to/whisper-cli"),
            Path("/path/to/model"),
            "en",
            1,
            self.mock_logger,
            symbol_words_to_symbols=True,
        )
        result = transcriber._symbol_word_to_symbol("hello question mark world")
        self.assertEqual(result, "hello? world")


if __name__ == "__main__":
    unittest.main()
