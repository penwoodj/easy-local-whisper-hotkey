"""Daemon state manager for FastAPI endpoints.

Uses a class to maintain daemon subprocess state,
ensuring thread-safe access from FastAPI endpoints.
"""
import subprocess
import threading
import logging
from datetime import datetime
from typing import Optional


logger = logging.getLogger(__name__)


class DaemonState:
    """Thread-safe daemon subprocess state manager."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._process: Optional[subprocess.Popen] = None
        self._started_at: Optional[str] = None
        self._last_transcription: str = ""
    
    def start(self, args: list[str]) -> dict[str, any]:
        """Start daemon subprocess with given args."""
        with self._lock:
            # Check if still alive
            if self._process is not None:
                try:
                    self._process.poll()
                    if self._process.returncode is None:
                        raise RuntimeError("Daemon already running")
                except Exception:
                    pass
                self._process = None
            
            # Load current config and start
            try:
                self._process = subprocess.Popen(
                    ["easy-local-whisper-hotkey", "run"] + args,
                    start_new_session=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self._started_at = datetime.now().isoformat()
                logger.info(f"Daemon started with PID {self._process.pid}")
                
                return {
                    "started": True,
                    "pid": self._process.pid,
                }
            except Exception as e:
                logger.error(f"Failed to start daemon: {e}")
                raise RuntimeError(f"Failed to start daemon: {e}")
    
    def stop(self) -> dict[str, any]:
        """Stop daemon subprocess."""
        with self._lock:
            if self._process is None:
                raise RuntimeError("Daemon not running")
            
            try:
                self._process.poll()
                if self._process.returncode is not None:
                    raise RuntimeError("Daemon not running (already stopped)")
                
                # Send SIGTERM
                self._process.terminate()
                
                # Wait up to 5 seconds
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("Daemon did not stop gracefully, sending SIGKILL")
                    self._process.kill()
                    self._process.wait()
                
                self._process = None
                self._started_at = None
                self._last_transcription = ""
                
                logger.info("Daemon stopped")
                
                return {
                    "stopped": True,
                }
            except Exception as e:
                logger.error(f"Failed to stop daemon: {e}")
                raise RuntimeError(f"Failed to stop daemon: {e}")
    
    def get_status(self) -> dict[str, any]:
        """Get current daemon status."""
        with self._lock:
            is_running = self._process is not None
            
            # Check if process still alive
            if is_running and self._process:
                try:
                    self._process.poll()
                    if self._process.returncode is not None:
                        # Process exited
                        self._process = None
                        self._started_at = None
                        is_running = False
                except Exception:
                    pass
            
            return {
                "is_running": is_running,
                "pid": self._process.pid if self._process else None,
                "last_started": self._started_at,
                "stream_text": self._last_transcription,
            }
    
    def update_transcription(self, text: str) -> None:
        """Update the last transcription text."""
        with self._lock:
            self._last_transcription = text


# Global singleton instance
_daemon_state = DaemonState()


def get_daemon_state() -> DaemonState:
    """Get the global daemon state instance."""
    return _daemon_state
