import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from whisper_hotkey import app


class SingleInstanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.lock_file = Path(self.temp_dir) / "test.lock"

    def tearDown(self) -> None:
        if self.lock_file.exists():
            self.lock_file.unlink()
        os.rmdir(self.temp_dir)

    def test_acquire_creates_lock_file(self) -> None:
        instance = app.SingleInstance(self.lock_file)
        instance.acquire()
        self.assertTrue(self.lock_file.exists())

    def test_acquire_writes_pid(self) -> None:
        instance = app.SingleInstance(self.lock_file)
        instance.acquire()
        content = self.lock_file.read_text()
        pid = os.getpid()
        self.assertEqual(content.strip(), str(pid))

    def test_acquire_second_instance_raises_error(self) -> None:
        instance1 = app.SingleInstance(self.lock_file)
        instance1.acquire()

        instance2 = app.SingleInstance(self.lock_file)
        with self.assertRaises(RuntimeError) as context:
            instance2.acquire()
        self.assertIn("another whisper daemon instance is already running", str(context.exception))

    def test_acquire_after_handle_cleanup(self) -> None:
        instance1 = app.SingleInstance(self.lock_file)
        instance1.acquire()
        instance1.handle.close()

        instance2 = app.SingleInstance(self.lock_file)
        instance2.acquire()
        self.assertTrue(self.lock_file.exists())

    def test_acquire_with_temp_directory(self) -> None:
        temp_dir = Path(tempfile.mkdtemp())
        lock_file = temp_dir / "daemon.lock"
        try:
            instance = app.SingleInstance(lock_file)
            instance.acquire()
            self.assertTrue(lock_file.exists())
        finally:
            if lock_file.exists():
                lock_file.unlink()
            temp_dir.rmdir()

    def test_acquire_with_nonexistent_parent(self) -> None:
        lock_file = Path("/nonexistent/path/lock.lock")
        instance = app.SingleInstance(lock_file)
        with self.assertRaises(FileNotFoundError):
            instance.acquire()

    def test_acquire_lock_exclusive(self) -> None:
        import fcntl

        instance1 = app.SingleInstance(self.lock_file)
        instance1.acquire()

        instance2 = app.SingleInstance(self.lock_file)
        instance2.handle = instance2.path.open("w")

        try:
            fcntl.flock(instance2.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.fail("Should have raised OSError (lock should be held)")
        except OSError:
            pass


if __name__ == "__main__":
    unittest.main()
