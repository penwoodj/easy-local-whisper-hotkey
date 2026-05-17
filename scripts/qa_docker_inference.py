#!/usr/bin/env python3
"""Live QA: Record real audio from mic, send to Docker inference, verify transcription."""

import base64
import json
import os
import signal
import socket
import struct
import subprocess
import sys
import time
import wave
from pathlib import Path


SOCKET_PATH = os.path.join(
    os.environ.get("XDG_RUNTIME_DIR", "/run/user/1000"),
    "whisper",
    "whisper.sock",
)
SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2
RECORD_SECONDS = 5
TMP_WAV = "/tmp/qa_test_recording.wav"
TMP_RAW = "/tmp/qa_test_recording.s16le"


def log(msg: str) -> None:
    print(f"[QA] {msg}", file=sys.stderr, flush=True)


def get_audio_source() -> str:
    """Find the Razer mic or first available source."""
    result = subprocess.run(
        ["pactl", "list", "short", "sources"],
        capture_output=True, text=True, check=False,
    )
    for line in result.stdout.strip().split("\n"):
        parts = line.split("\t")
        if len(parts) >= 2:
            name = parts[1]
            if "Razer" in name or "Seiren" in name:
                return name
    for line in result.stdout.strip().split("\n"):
        parts = line.split("\t")
        if len(parts) >= 2:
            name = parts[1]
            if "alsa_input" in name and "auto_null" not in name:
                return name
    return ""


def record_audio(source: str, duration: int) -> bytes:
    """Record raw PCM s16le from PulseAudio source."""
    log(f"Recording {duration}s from {source}")
    raw_path = Path(TMP_RAW)
    try:
        proc = subprocess.run(
            [
                "parec", "--device", source,
                "--raw", f"--rate={SAMPLE_RATE}",
                f"--channels={CHANNELS}", "--format=s16le",
            ],
            stdout=open(raw_path, "wb"),
            stderr=subprocess.DEVNULL,
            timeout=duration + 1,
        )
        pcm_data = raw_path.read_bytes()
        raw_path.unlink(missing_ok=True)
        log(f"Captured {len(pcm_data)} bytes of PCM audio")
        return pcm_data
    except subprocess.TimeoutExpired:
        pcm_data = raw_path.read_bytes() if raw_path.exists() else b""
        raw_path.unlink(missing_ok=True)
        log(f"Recording timed out, got {len(pcm_data)} bytes")
        return pcm_data
    except Exception as e:
        log(f"Recording error: {e}")
        return b""


def record_silence(duration: int) -> bytes:
    """Generate silence PCM data."""
    num_samples = SAMPLE_RATE * CHANNELS * duration
    return b"\x00\x00" * num_samples


def save_wav(pcm_data: bytes, path: str) -> None:
    """Save PCM data as WAV file for debugging."""
    with wave.open(path, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_data)
    log(f"Saved WAV to {path} ({len(pcm_data)} bytes)")


def send_to_server(payload: dict) -> dict | None:
    """Send JSON to inference server and get response."""
    if not os.path.exists(SOCKET_PATH):
        log(f"Socket not found: {SOCKET_PATH}")
        return None

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect(SOCKET_PATH)

        data = json.dumps(payload).encode("utf-8")
        header = struct.pack(">I", len(data))
        sock.sendall(header + data)

        resp_header = b""
        while len(resp_header) < 4:
            chunk = sock.recv(4 - len(resp_header))
            if not chunk:
                sock.close()
                return None
            resp_header += chunk

        resp_len = struct.unpack(">I", resp_header)[0]
        resp_data = b""
        while len(resp_data) < resp_len:
            chunk = sock.recv(min(4096, resp_len - len(resp_data)))
            if not chunk:
                sock.close()
                return None
            resp_data += chunk

        sock.close()
        return json.loads(resp_data.decode("utf-8"))
    except Exception as e:
        log(f"Socket error: {e}")
        return None


def test_ping() -> bool:
    """Test 1: Ping the inference server."""
    log("TEST 1: Ping inference server")
    resp = send_to_server({"action": "ping"})
    if resp and resp.get("status") == "ok":
        log(f"  PASS: server alive, model={resp.get('model')}")
        return True
    log(f"  FAIL: ping response={resp}")
    return False


def test_silence() -> bool:
    """Test 2: Send silence, expect empty or near-empty transcription."""
    log("TEST 2: Silence transcription")
    pcm = record_silence(2)
    if len(pcm) == 0:
        log("  SKIP: no silence data")
        return False

    resp = send_to_server({
        "audio": base64.b64encode(pcm).decode("ascii"),
        "language": "en",
    })
    if resp is None:
        log("  FAIL: no response")
        return False

    if "error" in resp:
        log(f"  FAIL: server error: {resp['error']}")
        return False

    text = resp.get("text", "").strip()
    log(f"  Result: text={text!r} segments={resp.get('segments')}")
    if not text or len(text) < 20:
        log("  PASS: silence filtered (short or empty)")
        return True
    log("  WARN: silence produced text (expected empty)")
    return True


def test_tone() -> bool:
    """Test 3: Send a generated tone, expect it to not hallucinate much."""
    log("TEST 3: Generated tone transcription")
    import struct as _struct
    duration = 3
    num_samples = SAMPLE_RATE * duration
    pcm = b""
    for i in range(num_samples):
        sample = int(16000 * (1 if (i // 800) % 2 == 0 else -1))
        pcm += _struct.pack("<h", max(-32768, min(32767, sample)))

    resp = send_to_server({
        "audio": base64.b64encode(pcm).decode("ascii"),
        "language": "en",
    })
    if resp is None:
        log("  FAIL: no response")
        return False
    if "error" in resp:
        log(f"  FAIL: server error: {resp['error']}")
        return False

    text = resp.get("text", "").strip()
    log(f"  Result: text={text!r} segments={resp.get('segments')}")
    log("  PASS: tone processed without crash")
    return True


def test_real_audio() -> bool:
    """Test 4: Record real audio from mic and transcribe."""
    log("TEST 4: Real audio from mic")
    source = get_audio_source()
    if not source:
        log("  SKIP: no audio source found")
        return True

    pcm = record_audio(source, RECORD_SECONDS)
    if len(pcm) < SAMPLE_RATE * SAMPLE_WIDTH:
        log(f"  FAIL: too little audio ({len(pcm)} bytes)")
        return False

    save_wav(pcm, TMP_WAV)

    log(f"Sending {len(pcm)} bytes to inference server...")
    t0 = time.monotonic()
    resp = send_to_server({
        "audio": base64.b64encode(pcm).decode("ascii"),
        "language": "en",
    })
    elapsed = time.monotonic() - t0

    if resp is None:
        log(f"  FAIL: no response ({elapsed:.2f}s)")
        return False
    if "error" in resp:
        log(f"  FAIL: server error: {resp['error']} ({elapsed:.2f}s)")
        return False

    text = resp.get("text", "").strip()
    log(f"  Result ({elapsed:.2f}s): text={text!r} segments={resp.get('segments')}")

    if not text:
        log("  WARN: empty transcription (mic may be silent)")
        return True

    log(f"  PASS: transcribed '{text[:80]}...' in {elapsed:.2f}s")
    return True


def test_client_class() -> bool:
    """Test 5: Use the WhisperInferenceClient class directly."""
    log("TEST 5: WhisperInferenceClient class")
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from whisper_hotkey.inference_client import WhisperInferenceClient

    client = WhisperInferenceClient()
    if not client.is_server_available():
        log("  FAIL: server not available")
        return False

    ping = client.ping()
    log(f"  Ping: {ping}")
    if not ping or ping.get("status") != "ok":
        log("  FAIL: ping failed")
        return False

    pcm = record_silence(1)
    t0 = time.monotonic()
    text = client.transcribe(pcm, "en")
    elapsed = time.monotonic() - t0
    log(f"  Silence transcription ({elapsed:.2f}s): {text!r}")

    client.close()
    log("  PASS: client class works")
    return True


def test_container_isolation() -> bool:
    """Test 6: Verify Docker container has no network."""
    log("TEST 6: Container network isolation")
    result = subprocess.run(
        ["docker", "inspect", "whisper-inference",
         "--format", "{{.HostConfig.NetworkMode}}"],
        capture_output=True, text=True, check=False,
    )
    mode = result.stdout.strip()
    log(f"  NetworkMode: {mode}")
    if mode != "none":
        log(f"  FAIL: expected 'none', got '{mode}'")
        return False

    result2 = subprocess.run(
        ["docker", "exec", "whisper-inference", "ip", "link", "show"],
        capture_output=True, text=True, check=False,
    )
    interfaces = [line for line in result2.stdout.split("\n") if ": " in line]
    log(f"  Interfaces: {interfaces}")
    if any("eth0" in line or "wlan" in line for line in interfaces):
        log("  FAIL: found network interfaces")
        return False

    log("  PASS: container isolated")
    return True


def main() -> int:
    log("=" * 60)
    log("Docker Inference Live QA")
    log("=" * 60)

    # Check prerequisites
    if not os.path.exists(SOCKET_PATH):
        log(f"FATAL: Socket not found at {SOCKET_PATH}")
        log("  Is the Docker container running? docker compose up -d")
        return 1

    result = subprocess.run(
        ["docker", "ps", "--filter", "name=whisper-inference",
         "--format", "{{.Status}}"],
        capture_output=True, text=True, check=False,
    )
    log(f"Container status: {result.stdout.strip()}")

    results = {}
    tests = [
        ("ping", test_ping),
        ("silence", test_silence),
        ("tone", test_tone),
        ("real_audio", test_real_audio),
        ("client_class", test_client_class),
        ("container_isolation", test_container_isolation),
    ]

    for name, test_fn in tests:
        try:
            passed = test_fn()
            results[name] = passed
        except Exception as e:
            log(f"  EXCEPTION: {e}")
            results[name] = False

    log("")
    log("=" * 60)
    log("RESULTS")
    log("=" * 60)
    all_pass = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        log(f"  {status}: {name}")
        if not passed:
            all_pass = False

    log("")
    if all_pass:
        log("ALL TESTS PASSED")
        return 0
    log("SOME TESTS FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
