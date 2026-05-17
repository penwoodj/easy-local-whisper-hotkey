#!/usr/bin/env python3
# Build with:
#   FROM python:3.12-slim
#   RUN pip install faster-whisper numpy
#   COPY src/whisper_hotkey/inference_server.py /usr/local/bin/inference_server.py
#   ENTRYPOINT ["python", "/usr/local/bin/inference_server.py"]

import os
import sys
import json
import base64
import signal
import socket
import struct
import threading
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

SILENCE_WORDS = {"you", "yeah", "uh", "um", "mm", "hmm", "mmm", "hm", "shh"}
SILENCE_PHRASES = {
    "thank you for watching",
    "thank you for listening",
    "subscribe to my channel",
}

CONFIG = {
    "model": os.getenv("WHISPER_MODEL", "base.en"),
    "compute_type": os.getenv("WHISPER_COMPUTE_TYPE", "int8"),
    "device": os.getenv("WHISPER_DEVICE", "cpu"),
    "socket_path": os.getenv("WHISPER_SOCKET_PATH", "/run/whisper/whisper.sock"),
    "language": os.getenv("WHISPER_LANGUAGE", "en"),
    "vad_threshold": float(os.getenv("WHISPER_VAD_THRESHOLD", "0.5")),
    "download_root": os.getenv("WHISPER_DOWNLOAD_ROOT", "/models"),
}

shutdown_event = threading.Event()


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def send_json(sock: socket.socket, data: dict) -> None:
    payload = json.dumps(data).encode("utf-8")
    header = struct.pack(">I", len(payload))
    try:
        sock.sendall(header + payload)
    except (BrokenPipeError, ConnectionResetError):
        pass


def recv_json(sock: socket.socket) -> dict | None:
    try:
        header = sock.recv(4)
        if len(header) < 4:
            return None
        msg_len = struct.unpack(">I", header)[0]
        payload = b""
        while len(payload) < msg_len:
            chunk = sock.recv(min(4096, msg_len - len(payload)))
            if not chunk:
                return None
            payload += chunk
        return json.loads(payload.decode("utf-8"))
    except (ConnectionResetError, json.JSONDecodeError, struct.error):
        return None


def is_silence_hallucination(text: str) -> bool:
    text = text.strip().lower()
    if text in SILENCE_WORDS:
        return True
    for phrase in SILENCE_PHRASES:
        if phrase in text:
            return True
    return False


def handle_connection(sock: socket.socket, model: WhisperModel) -> None:
    import time as _time
    t0 = _time.monotonic()
    try:
        request = recv_json(sock)
        if not request:
            log(f"Connection: no request received ({_time.monotonic()-t0:.2f}s)")
            return

        if request.get("action") == "ping":
            send_json(sock, {"status": "ok", "model": CONFIG["model"]})
            log(f"Ping answered ({_time.monotonic()-t0:.2f}s)")
            return

        audio_b64 = request.get("audio")
        language = request.get("language", CONFIG["language"])

        if not audio_b64:
            send_json(sock, {"error": "missing audio field"})
            return

        audio_bytes = base64.b64decode(audio_b64)
        log(f"Transcribing {len(audio_bytes)} bytes, lang={language}")

        try:
            audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0

            t1 = _time.monotonic()
            segments, info = model.transcribe(
                audio_float32,
                vad_filter=True,
                vad_parameters={
                    "threshold": CONFIG["vad_threshold"],
                    "min_speech_duration_ms": 250,
                    "min_silence_duration_ms": 500,
                },
                word_timestamps=True,
                no_speech_threshold=0.7,
                compression_ratio_threshold=2.2,
                language=language,
            )

            segment_list = []
            full_text = ""

            for seg in segments:
                text = seg.text.strip()
                if not text or is_silence_hallucination(text):
                    continue
                segment_list.append(text)
                full_text += (" " if full_text else "") + text

            infer_time = _time.monotonic() - t1
            log(
                f"Result: {len(full_text)} chars, {len(segment_list)} segments "
                f"in {infer_time:.2f}s: {full_text[:80]!r}"
            )

            send_json(
                sock,
                {
                    "text": full_text,
                    "segments": len(segment_list),
                },
            )

        except Exception as e:
            log(f"Transcription error: {e}")
            send_json(sock, {"error": str(e)})
    except Exception as e:
        log(f"Connection error: {e}")
    finally:
        total = _time.monotonic() - t0
        try:
            sock.close()
        except Exception:
            pass


def main() -> None:
    log(f"Loading model: {CONFIG['model']} from {CONFIG['download_root']}")
    model = WhisperModel(
        CONFIG["model"],
        device=CONFIG["device"],
        compute_type=CONFIG["compute_type"],
        download_root=CONFIG["download_root"],
    )
    log(f"Model loaded. Listening on {CONFIG['socket_path']}")

    socket_path = Path(CONFIG["socket_path"])
    socket_path.parent.mkdir(parents=True, exist_ok=True)

    if socket_path.exists():
        socket_path.unlink()

    server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server_sock.bind(CONFIG["socket_path"])
    server_sock.listen(5)
    socket_path.chmod(0o600)

    signal.signal(signal.SIGTERM, lambda sig, frame: shutdown_event.set())
    signal.signal(signal.SIGINT, lambda sig, frame: shutdown_event.set())

    server_sock.settimeout(0.5)

    while not shutdown_event.is_set():
        try:
            client_sock, _ = server_sock.accept()
            thread = threading.Thread(
                target=handle_connection,
                args=(client_sock, model),
                daemon=True,
            )
            thread.start()
        except TimeoutError:
            continue
        except Exception as e:
            if not shutdown_event.is_set():
                log(f"Error accepting connection: {e}")

    server_sock.close()
    if socket_path.exists():
        socket_path.unlink()
    log("Shutdown complete")


if __name__ == "__main__":
    main()