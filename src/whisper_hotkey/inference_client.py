import base64
import json
import logging
import os
import socket
import struct
import threading
from typing import Optional


class WhisperInferenceClient:
    def __init__(
        self,
        socket_path: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.socket_path = socket_path or os.path.join(
            os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"),
            "whisper",
            "whisper.sock",
        )
        self.logger = logger or logging.getLogger(__name__)
        self._socket: Optional[socket.socket] = None
        self._lock = threading.Lock()

    def _connect(self) -> bool:
        with self._lock:
            if self._socket is not None:
                return True

            if not os.path.exists(self.socket_path):
                return False

            try:
                self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self._socket.settimeout(5)
                self._socket.connect(self.socket_path)
                return True
            except (OSError, socket.error, TimeoutError) as e:
                self.logger.error(f"Socket connection failed: {e}")
                self._socket = None
                return False

    def _disconnect(self):
        with self._lock:
            if self._socket is not None:
                try:
                    self._socket.close()
                except OSError:
                    pass
                self._socket = None

    def _send(self, data: bytes) -> bool:
        if self._socket is None:
            if not self._connect():
                return False

        try:
            self._socket.sendall(data)
            return True
        except (OSError, socket.error, TimeoutError) as e:
            self.logger.error(f"Send failed: {e}")
            self._disconnect()
            return False

    def _recv_all(self, n: int) -> Optional[bytes]:
        data = bytearray()
        while len(data) < n:
            try:
                chunk = self._socket.recv(n - len(data))
                if not chunk:
                    return None
                data.extend(chunk)
            except (OSError, socket.error, TimeoutError) as e:
                self.logger.error(f"Receive failed: {e}")
                self._disconnect()
                return None
        return bytes(data)

    def _recv_message(self) -> Optional[dict]:
        length_data = self._recv_all(4)
        if length_data is None:
            return None

        length = struct.unpack(">I", length_data)[0]
        payload = self._recv_all(length)
        if payload is None:
            return None

        try:
            return json.loads(payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self.logger.error(f"Failed to parse JSON: {e}")
            return None

    def _send_message(self, msg: dict) -> bool:
        payload = json.dumps(msg).encode("utf-8")
        frame = struct.pack(">I", len(payload)) + payload
        return self._send(frame)

    def transcribe(self, pcm_data: bytes, language: str = "en") -> str:
        import time as _time
        t0 = _time.monotonic()
        audio_size = len(pcm_data)
        request = {
            "audio": base64.b64encode(pcm_data).decode("ascii"),
            "language": language,
        }

        for attempt in range(2):
            if not self._send_message(request):
                self.logger.warning(f"InferenceClient: send failed attempt {attempt+1}/2 ({audio_size} bytes)")
                continue

            if self._socket is not None:
                self._socket.settimeout(30)
            response = self._recv_message()
            if self._socket is not None:
                self._socket.settimeout(5)

            if response is None:
                self.logger.warning(f"InferenceClient: recv failed attempt {attempt+1}/2")
                self._disconnect()
                continue

            if "error" in response:
                self.logger.error(f"InferenceClient: server error: {response['error']}")
                self._disconnect()
                return ""

            text = response.get("text", "")
            elapsed = _time.monotonic() - t0
            self.logger.info(
                f"InferenceClient: OK {audio_size}B → {len(text)} chars in {elapsed:.2f}s "
                f"(segments={response.get('segments', '?')})"
            )
            self._disconnect()
            return text

        elapsed = _time.monotonic() - t0
        self.logger.error(f"InferenceClient: all attempts failed after {elapsed:.2f}s ({audio_size} bytes)")
        return ""

    def is_server_available(self) -> bool:
        result = self.ping()
        return result is not None and result.get("status") == "ok"

    def ping(self) -> Optional[dict]:
        self._disconnect()
        if not self._send_message({"action": "ping"}):
            return None
        result = self._recv_message()
        self._disconnect()
        return result

    def close(self):
        self._disconnect()

    def __del__(self):
        self.close()