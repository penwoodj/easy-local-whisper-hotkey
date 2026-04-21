import os
import tempfile
import time
import unittest
from pathlib import Path

from whisper_hotkey import app


class LoggerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = Path(self.temp_dir) / "test.log"

    def tearDown(self) -> None:
        if self.log_file.exists():
            self.log_file.unlink()
        os.rmdir(self.temp_dir)

    def test_logger_init_creates_file_on_first_write(self) -> None:
        logger = app.Logger(self.log_file)
        self.assertFalse(self.log_file.exists())
        logger.log("Test message")
        self.assertTrue(self.log_file.exists())

    def test_logger_log_creates_file(self) -> None:
        logger = app.Logger(self.log_file)
        logger.log("Test message")
        self.assertTrue(self.log_file.exists())

    def test_logger_log_writes_message(self) -> None:
        logger = app.Logger(self.log_file)
        logger.log("Test message")
        content = self.log_file.read_text()
        self.assertIn("Test message", content)

    def test_logger_log_includes_timestamp(self) -> None:
        logger = app.Logger(self.log_file)
        logger.log("Test message")
        content = self.log_file.read_text()
        import re
        self.assertRegex(content, r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]')

    def test_logger_log_appends_messages(self) -> None:
        logger = app.Logger(self.log_file)
        logger.log("First message")
        logger.log("Second message")
        content = self.log_file.read_text()
        self.assertIn("First message", content)
        self.assertIn("Second message", content)

    def test_logger_log_newline_after_message(self) -> None:
        logger = app.Logger(self.log_file)
        logger.log("Test")
        content = self.log_file.read_text()
        self.assertTrue(content.endswith("\n"))

    def test_logger_log_empty_string(self) -> None:
        logger = app.Logger(self.log_file)
        logger.log("")
        content = self.log_file.read_text()
        # Empty message produces timestamp followed by brackets and space
        self.assertIn("]", content)
        self.assertIn("[", content)

    def test_logger_log_unicode(self) -> None:
        logger = app.Logger(self.log_file)
        logger.log("Héllo wörld 🌍")
        content = self.log_file.read_text()
        self.assertIn("Héllo wörld 🌍", content)

    def test_logger_log_special_characters(self) -> None:
        logger = app.Logger(self.log_file)
        logger.log("Test\nSpecial\tChars")
        content = self.log_file.read_text()
        self.assertIn("Test", content)

    def test_logger_multiple_loggers_same_file(self) -> None:
        logger1 = app.Logger(self.log_file)
        logger2 = app.Logger(self.log_file)
        logger1.log("Message from logger1")
        logger2.log("Message from logger2")
        content = self.log_file.read_text()
        self.assertIn("Message from logger1", content)
        self.assertIn("Message from logger2", content)

    def test_logger_thread_safety(self) -> None:
        import threading

        logger = app.Logger(self.log_file)
        num_threads = 10
        messages_per_thread = 100

        def log_messages(thread_id: int) -> None:
            for i in range(messages_per_thread):
                logger.log(f"Thread {thread_id} message {i}")

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=log_messages, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        content = self.log_file.read_text()
        line_count = content.count("\n")
        self.assertEqual(line_count, num_threads * messages_per_thread)

    def test_logger_log_with_newline_in_message(self) -> None:
        logger = app.Logger(self.log_file)
        logger.log("Line 1\nLine 2")
        content = self.log_file.read_text()
        self.assertIn("Line 1", content)
        self.assertIn("Line 2", content)

    def test_logger_log_very_long_message(self) -> None:
        logger = app.Logger(self.log_file)
        long_message = "x" * 10000
        logger.log(long_message)
        content = self.log_file.read_text()
        self.assertIn(long_message, content)

    def test_logger_existing_file_appends(self) -> None:
        self.log_file.write_text("Existing content\n")
        logger = app.Logger(self.log_file)
        logger.log("New message")
        content = self.log_file.read_text()
        self.assertIn("Existing content", content)
        self.assertIn("New message", content)

    def test_logger_path_attribute(self) -> None:
        logger = app.Logger(self.log_file)
        self.assertEqual(logger.path, self.log_file)

    def test_logger_temp_directory(self) -> None:
        temp_dir = Path(tempfile.mkdtemp())
        log_file = temp_dir / "test.log"
        try:
            logger = app.Logger(log_file)
            logger.log("Test")
            self.assertTrue(log_file.exists())
            content = log_file.read_text()
            self.assertIn("Test", content)
        finally:
            if log_file.exists():
                log_file.unlink()
            temp_dir.rmdir()


if __name__ == "__main__":
    unittest.main()
