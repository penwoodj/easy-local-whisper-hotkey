import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from whisper_hotkey import app


class RecorderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_logger = Mock()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_recorder_init(self) -> None:
        recorder = app.Recorder("test-source", self.mock_logger)
        self.assertEqual(recorder.source, "test-source")
        self.assertEqual(recorder.logger, self.mock_logger)
        self.assertEqual(recorder.bytes_written, 0)
        self.assertIsNone(recorder.proc)
        self.assertIsNotNone(recorder.raw_path)
        self.assertTrue(recorder.raw_path.exists())

    @patch('subprocess.Popen')
    @patch('threading.Thread')
    def test_recorder_start(self, mock_thread_class, mock_popen) -> None:
        mock_proc = MagicMock()
        mock_proc.stdout = MagicMock()
        mock_proc.stderr = MagicMock()
        mock_popen.return_value = mock_proc

        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        recorder = app.Recorder("test-source", self.mock_logger)
        recorder.start()

        mock_popen.assert_called_once()
        self.assertEqual(mock_thread_class.call_count, 2)
        mock_thread.start.assert_called()
        self.assertEqual(recorder.proc, mock_proc)

    @patch('subprocess.Popen')
    def test_recorder_start_command(self, mock_popen) -> None:
        mock_proc = MagicMock()
        mock_proc.stdout = MagicMock()
        mock_proc.stderr = MagicMock()
        mock_popen.return_value = mock_proc

        with patch('threading.Thread'):
            recorder = app.Recorder("test-source", self.mock_logger)
            recorder.start()

            args, kwargs = mock_popen.call_args
            command = args[0]
            self.assertIn("parec", command)
            self.assertIn("--record", command)
            self.assertIn("--raw", command)
            self.assertIn("-d", command)
            self.assertIn("test-source", command)

    def test_recorder_stop_no_process(self) -> None:
        recorder = app.Recorder("test-source", self.mock_logger)
        recorder.proc = None
        recorder.stop()
        self.mock_logger.log.assert_not_called()

    @patch('subprocess.Popen')
    def test_recorder_stop_terminates_process(self, mock_popen) -> None:
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.wait.return_value = None
        mock_popen.return_value = mock_proc

        with patch('threading.Thread'):
            recorder = app.Recorder("test-source", self.mock_logger)
            recorder.start()
            recorder.stop()

        mock_proc.terminate.assert_called_once()
        mock_proc.wait.assert_called_once()

    @patch('subprocess.Popen')
    def test_recorder_stop_kills_on_timeout(self, mock_popen) -> None:
        from subprocess import TimeoutExpired

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.wait.side_effect = [TimeoutExpired("test", 2), None]
        mock_popen.return_value = mock_proc

        with patch('threading.Thread'):
            recorder = app.Recorder("test-source", self.mock_logger)
            recorder.start()
            recorder.stop()

        mock_proc.terminate.assert_called_once()
        mock_proc.kill.assert_called_once()

    def test_recorder_available(self) -> None:
        recorder = app.Recorder("test-source", self.mock_logger)
        recorder.bytes_written = 1024
        self.assertEqual(recorder.available(), 1024)

    def test_recorder_read_segment(self) -> None:
        recorder = app.Recorder("test-source", self.mock_logger)
        test_data = b"test audio data" * 100
        with recorder.raw_path.open("wb") as f:
            f.write(test_data)
        recorder.bytes_written = len(test_data)

        result = recorder.read_segment(0, len(test_data))
        self.assertEqual(result, test_data)

    def test_recorder_read_segment_partial(self) -> None:
        recorder = app.Recorder("test-source", self.mock_logger)
        test_data = b"test audio data" * 100
        with recorder.raw_path.open("wb") as f:
            f.write(test_data)
        recorder.bytes_written = len(test_data)

        result = recorder.read_segment(0, 20)
        self.assertEqual(result, test_data[:20])

    def test_recorder_read_segment_beyond_available(self) -> None:
        recorder = app.Recorder("test-source", self.mock_logger)
        test_data = b"test audio data" * 100
        with recorder.raw_path.open("wb") as f:
            f.write(test_data)

        recorder.bytes_written = len(test_data)
        result = recorder.read_segment(len(test_data), len(test_data) + 100)
        self.assertEqual(result, b"")

    def test_recorder_cleanup(self) -> None:
        recorder = app.Recorder("test-source", self.mock_logger)
        self.assertTrue(recorder.raw_path.exists())
        recorder.cleanup()
        self.assertFalse(recorder.raw_path.exists())

    def test_recorder_cleanup_nonexistent_file(self) -> None:
        recorder = app.Recorder("test-source", self.mock_logger)
        recorder.raw_path.unlink()
        recorder.cleanup()
        self.assertFalse(recorder.raw_path.exists())


if __name__ == "__main__":
    unittest.main()
