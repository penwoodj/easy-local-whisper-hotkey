import unittest

from whisper_hotkey import app


class TranscriptProcessingTests(unittest.TestCase):
    def test_clean_transcript_strips_bracket_lines(self) -> None:
        text = "[00:00:00] noise\nHello there\n[BLANK_AUDIO]\nGeneral Kenobi"
        self.assertEqual(app.clean_transcript(text), "noise Hello there General Kenobi")

    def test_compute_append_text_deduplicates_overlap(self) -> None:
        history = "what I would really like you to".split()
        new_text = "like you to do is make it so"
        self.assertEqual(app.compute_append_text(history, new_text), "do is make it so")

    def test_compute_append_text_returns_all_new_words_without_overlap(self) -> None:
        history = "hello world".split()
        new_text = "completely different sentence"
        self.assertEqual(app.compute_append_text(history, new_text), new_text)

    def test_parse_preferred_sources_ignores_empty_entries(self) -> None:
        self.assertEqual(
            app.parse_preferred_sources("mic1, ,mic2,,"),
            ["mic1", "mic2"],
        )


if __name__ == "__main__":
    unittest.main()
