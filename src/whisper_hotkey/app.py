import argparse
import ctypes
import difflib
import fcntl
import os
import queue
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import threading
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .postprocessor import PostProcessor, PostProcessMode, PostProcessTrigger
from .inference_client import WhisperInferenceClient

try:
    import numpy as np
    from faster_whisper import WhisperModel
    HAS_FASTER_WHISPER = True
except ImportError:
    HAS_FASTER_WHISPER = False


HOME = Path.home()
PACKAGE_NAME = "whisper-hotkey"
LEGACY_WHISPER_CLI = HOME / "code/opencode-infinite/whisper.cpp/build/bin/whisper-cli"
XDG_DATA_HOME = Path(os.environ.get("XDG_DATA_HOME", HOME / ".local/share"))
DEFAULT_MODEL = XDG_DATA_HOME / PACKAGE_NAME / "models/ggml-base.en.bin"
DEFAULT_LOG_FILE = Path("/tmp/whisper_hotkey.log")
LOCK_FILE = Path("/tmp/whisper_hotkey.lock")
DEFAULT_RAZER_SOURCE = "alsa_input.usb-Razer_Inc_Razer_Seiren_Mini_UC2148L03300931-00.mono-fallback"
DEFAULT_WEBCAM_SOURCE = "alsa_input.usb-Anker_PowerConf_C200_Anker_PowerConf_C200_ACNV9P0C52101128-02.analog-stereo"
DEFAULT_PREFERRED_SOURCES = [
    DEFAULT_RAZER_SOURCE,
    DEFAULT_WEBCAM_SOURCE,
]
RELEASE_GRACE_SECONDS = 0.3

SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2
BYTES_PER_SECOND = SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH
MAX_RECORDING_BYTES = 100 * 1024 * 1024  # 100MB max recording (~52 minutes at 32KB/s)

KEY_PRESS = 2
KEY_RELEASE = 3
GRAB_MODE_ASYNC = 1
CONTROL_MASK = 0x4
LOCK_MASK = 0x2
MOD2_MASK = 0x10
MOD5_MASK = 0x80
SHIFT_MASK = 0x1
MOD1_MASK = 0x8
XK_SPACE = 0x20
XK_CONTROL_L = 0xFFE3
XK_CONTROL_R = 0xFFE4
XK_SHIFT_L = 0xFFE1
XK_SHIFT_R = 0xFFE2
XK_ALT_L = 0xFFE9
XK_ALT_R = 0xFFEA
XK_M = 0x6D
XK_NUM_LOCK = 0xFF7F

_STRIP_PUNCT_RE = re.compile(r"[.,!?;:]")


def shell_join(parts):
    return " ".join(shlex.quote(part) for part in parts)


def shutil_which(command: str) -> str:
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / command
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return ""


def default_whisper_cli() -> Path:
    if os.environ.get("WHISPER_CLI"):
        return Path(os.environ["WHISPER_CLI"]).expanduser()
    discovered = shutil_which("whisper-cli")
    if discovered:
        return Path(discovered)
    return LEGACY_WHISPER_CLI


def parse_preferred_sources(raw_value: str | None) -> list[str]:
    if not raw_value:
        return list(DEFAULT_PREFERRED_SOURCES)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


class Logger:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()

    def log(self, message: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {message}\n"
        with self._lock:
            try:
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(line)
            except OSError:
                pass  # ENOSPC or other disk errors — never crash the daemon


class SingleInstance:
    def __init__(self, path: Path):
        self.path = path
        self.handle = None

    def acquire(self) -> None:
        self.handle = self.path.open("w")
        try:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise RuntimeError("another whisper daemon instance is already running") from None
        self.handle.write(f"{os.getpid()}\n")
        self.handle.flush()


FOCUS_OUT = 10


class XAnyEvent(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("serial", ctypes.c_ulong),
        ("send_event", ctypes.c_int),
        ("display", ctypes.c_void_p),
        ("window", ctypes.c_ulong),
    ]


class XKeyEvent(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("serial", ctypes.c_ulong),
        ("send_event", ctypes.c_int),
        ("display", ctypes.c_void_p),
        ("window", ctypes.c_ulong),
        ("root", ctypes.c_ulong),
        ("subwindow", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("x", ctypes.c_int),
        ("y", ctypes.c_int),
        ("x_root", ctypes.c_int),
        ("y_root", ctypes.c_int),
        ("state", ctypes.c_uint),
        ("keycode", ctypes.c_uint),
        ("same_screen", ctypes.c_int),
    ]


class XEvent(ctypes.Union):
    _fields_ = [
        ("type", ctypes.c_int),
        ("xany", XAnyEvent),
        ("xkey", XKeyEvent),
        ("pad", ctypes.c_long * 24),
    ]


@dataclass
class SegmentJob:
    index: int
    start: int
    end: int
    final: bool


def parse_args(argv: Sequence[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Long-running local Ctrl+Space whisper daemon for X11."
    )
    parser.add_argument(
        "--whisper-cli",
        default=str(default_whisper_cli()),
        help="Path to whisper.cpp's whisper-cli executable.",
    )
    parser.add_argument("--model", default=os.environ.get("WHISPER_MODEL", str(DEFAULT_MODEL)))
    parser.add_argument(
        "--source",
        default=os.environ.get("WHISPER_AUDIO_SOURCE", ""),
        help="Exact PulseAudio/PipeWire source name. Defaults to Razer if present, otherwise the default source.",
    )
    parser.add_argument(
        "--preferred-sources",
        default=os.environ.get(
            "WHISPER_PREFERRED_SOURCES",
            ",".join(DEFAULT_PREFERRED_SOURCES),
        ),
        help="Comma-separated source priority list used when --source is not set.",
    )
    parser.add_argument(
        "--chunk-seconds",
        type=float,
        default=float(os.environ.get("WHISPER_CHUNK_SECONDS", "3.5")),
    )
    parser.add_argument(
        "--overlap-seconds",
        type=float,
        default=float(os.environ.get("WHISPER_OVERLAP_SECONDS", "0.8")),
    )
    parser.add_argument(
        "--type-delay-ms",
        type=int,
        default=int(os.environ.get("WHISPER_TYPE_DELAY_MS", "1")),
    )
    parser.add_argument(
        "--language",
        default=os.environ.get("WHISPER_LANGUAGE", "en"),
    )
    parser.add_argument(
        "--suppress-regex",
        default=os.environ.get("WHISPER_SUPPRESS_REGEX", "[,.]"),
        help="Regex pattern to suppress specific tokens from whisper output.",
    )
    parser.add_argument(
        "--suppress-nst",
        action="store_true",
        default=os.environ.get("WHISPER_SUPPRESS_NST", "true").lower() == "true",
        help="Suppress non-speech tokens (sound effects, musical notes).",
    )
    parser.add_argument(
        "--smart-punctuation",
        action="store_true",
        default=os.environ.get("WHISPER_SMART_PUNCTUATION", "true").lower() == "true",
        help="Keep punctuation from explicit words (comma, period, etc.) while suppressing natural pauses.",
    )
    parser.add_argument(
        "--symbol-words-to-symbols",
        action="store_true",
        default=os.environ.get("WHISPER_SYMBOL_WORDS_TO_SYMBOLS", "false").lower() == "true",
        help="Convert spoken symbol names to actual symbols (comma → , period → .).",
    )
    parser.add_argument(
        "--direct-streaming",
        action="store_true",
        default=os.environ.get("WHISPER_DIRECT_STREAMING", "false").lower() == "true",
        help="Enable real-time text streaming as you speak.",
    )
    parser.add_argument(
        "--activation-mode",
        default=os.environ.get("WHISPER_ACTIVATION_MODE", "toggle"),
        choices=["hold", "toggle"],
        help="How to activate dictation: 'hold' (hold Ctrl+Space) or 'toggle' (press to start/stop).",
    )
    parser.add_argument(
        "--indicator",
        action="store_true",
        default=os.environ.get("WHISPER_INDICATOR", "true").lower() == "true",
        help="Show a cursor indicator when recording.",
    )
    parser.add_argument(
        "--postprocess",
        action="store_true",
        default=os.environ.get("WHISPER_POSTPROCESS", "false").lower() == "true",
        help="Enable grammar post-processing on toggle-off (default: false).",
    )
    parser.add_argument(
        "--postprocess-mode",
        default=os.environ.get("WHISPER_POSTPROCESS_MODE", "off"),
        choices=["off", "light", "aggressive", "agentic", "writing", "code", "structure", "persona", "clarity"],
        help="Post-processing mode (off, light, aggressive, agentic, writing, code, structure, persona, clarity).",
    )
    parser.add_argument(
        "--postprocess-trigger",
        default=os.environ.get("WHISPER_POSTPROCESS_TRIGGER", "manual"),
        choices=["always", "manual", "auto-long", "preview"],
        help="When to run post-processing (always, manual, auto-long, preview).",
    )
    parser.add_argument(
        "--log-file",
        default=os.environ.get("WHISPER_LOG_FILE", str(DEFAULT_LOG_FILE)),
    )
    parser.add_argument(
        "--test",
        nargs="?",
        const="3",
        metavar="SECONDS",
        help="Record once for a fixed number of seconds, transcribe, and type the result.",
    )
    return parser.parse_args(argv)


def list_sources(logger: Logger | None = None):
    try:
        result = subprocess.run(
            ["pactl", "list", "sources", "short"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("unable to query audio sources with pactl") from exc

    sources = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 2:
            sources.append(fields[1])
    if logger is not None:
        logger.log(f"Available sources: {', '.join(sources)}")
    return sources


def get_default_source():
    try:
        result = subprocess.run(
            ["pactl", "get-default-source"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""
    return result.stdout.strip()


def resolve_audio_source(
    preferred_source: str,
    preferred_sources: list[str],
    logger: Logger | None = None,
) -> str:
    sources = list_sources(logger)
    if not sources:
        raise RuntimeError("no PulseAudio/PipeWire sources found")

    if preferred_source:
        if preferred_source in sources:
            if logger is not None:
                logger.log(f"Using requested source: {preferred_source}")
            return preferred_source
        raise RuntimeError(f"requested source not found: {preferred_source}")

    for candidate in preferred_sources:
        if candidate in sources:
            if logger is not None:
                logger.log(f"Using preferred source: {candidate}")
            return candidate

    default_source = get_default_source()
    if default_source and default_source in sources and ".monitor" not in default_source:
        if logger is not None:
            logger.log(f"Using default source: {default_source}")
        return default_source

    for source in sources:
        if ".monitor" not in source:
            if logger is not None:
                logger.log(f"Using first capture source fallback: {source}")
            return source

    if logger is not None:
        logger.log(f"Using last-resort source fallback: {sources[0]}")
    return sources[0]


def resolve_audio_source_with_retry(
    preferred_source: str,
    preferred_sources: list[str],
    logger: Logger | None = None,
    max_retries: int = 6,
    retry_delay: float = 5.0,
) -> str:
    source = resolve_audio_source(preferred_source, preferred_sources, logger)
    attempts = 0
    while "auto_null" in source and attempts < max_retries:
        attempts += 1
        if logger is not None:
            logger.log(
                f"Audio source is auto_null (PipeWire not ready), "
                f"retrying in {retry_delay}s (attempt {attempts}/{max_retries})"
            )
        time.sleep(retry_delay)
        source = resolve_audio_source(preferred_source, preferred_sources, logger)
    if "auto_null" in source and logger is not None:
        logger.log(f"WARNING: still on auto_null after {max_retries} retries")
    return source


def collect_diagnostics(model: Path, whisper_cli: Path, preferred_sources: list[str]) -> dict[str, object]:
    commands = {
        "parec": bool(shutil_which("parec")),
        "pactl": bool(shutil_which("pactl")),
        "xdotool": bool(shutil_which("xdotool")),
    }
    sources = []
    source_error = ""
    try:
        sources = list_sources()
    except RuntimeError as exc:
        source_error = str(exc)

    display = os.environ.get("DISPLAY", "")
    return {
        "display": display,
        "xauthority": os.environ.get("XAUTHORITY", ""),
        "model_path": str(model),
        "model_exists": model.is_file(),
        "whisper_cli_path": str(whisper_cli),
        "whisper_cli_exists": whisper_cli.is_file(),
        "commands": commands,
        "preferred_sources": preferred_sources,
        "default_source": get_default_source(),
        "available_sources": sources,
        "source_error": source_error,
    }


def normalize_token(token: str) -> str:
    return re.sub(r"\W+", "", token).lower()


def clean_transcript(text: str) -> str:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            continue
        line = re.sub(r"^\[[^\]]+\]\s*", "", line)
        if not line:
            continue
        lines.append(line)
    return " ".join(lines).strip()


def compute_append_text(history_words, new_text: str) -> str:
    new_words = new_text.split()
    if not new_words:
        return ""

    normalized_history = [normalize_token(word) for word in history_words[-32:]]
    normalized_new = [normalize_token(word) for word in new_words]

    best_overlap = 0
    max_overlap = min(len(normalized_history), len(normalized_new), 10)
    for overlap in range(max_overlap, 0, -1):
        if normalized_history[-overlap:] == normalized_new[:overlap]:
            best_overlap = overlap
            break

    if best_overlap == 0 and max_overlap >= 2:
        for overlap in range(max_overlap, 1, -1):
            tail = normalized_history[-overlap:]
            head = normalized_new[:overlap]
            sim = difflib.SequenceMatcher(None, tail, head).ratio()
            if sim >= 0.8:
                best_overlap = overlap
                break

    append_words = new_words[best_overlap:]
    return " ".join(append_words).strip()


def _deduplicate_flush_text(text: str) -> str:
    words = text.split()
    if len(words) < 4:
        return text

    changed = True
    while changed:
        changed = False
        i = 0
        while i < len(words) - 2:
            removed = False
            for plen in range(min(8, len(words) - i), 2, -1):
                phrase = words[i:i + plen]
                for j in range(i + plen, min(i + plen + 12, len(words) - plen + 1)):
                    candidate = words[j:j + plen]
                    if phrase == candidate:
                        del words[j:j + plen]
                        changed = True
                        removed = True
                        break
                    if plen >= 3 and difflib.SequenceMatcher(None, phrase, candidate).ratio() >= 0.85:
                        del words[j:j + plen]
                        changed = True
                        removed = True
                        break
                if removed:
                    break
            if not removed:
                i += 1

    return " ".join(words)


class Recorder:
    def __init__(self, source: str, logger: Logger):
        self.source = source
        self.logger = logger
        self.bytes_written = 0
        self.lock = threading.Lock()
        self.stdout_thread = None
        self.stderr_thread = None
        self.proc = None
        fd, raw_path = tempfile.mkstemp(prefix="whisper_stream_", suffix=".s16le")
        os.close(fd)
        self.raw_path = Path(raw_path)

    def start(self) -> None:
        command = [
            "parec",
            "--record",
            "--raw",
            "-d",
            self.source,
            "--format=s16le",
            f"--rate={SAMPLE_RATE}",
            f"--channels={CHANNELS}",
            "--latency-msec=25",
            "--process-time-msec=25",
        ]
        self.logger.log(f"Starting recorder: {shell_join(command)}")
        self.proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        self.stdout_thread = threading.Thread(target=self._consume_stdout, daemon=True)
        self.stderr_thread = threading.Thread(target=self._consume_stderr, daemon=True)
        self.stdout_thread.start()
        self.stderr_thread.start()

    def _consume_stdout(self) -> None:
        assert self.proc is not None and self.proc.stdout is not None
        with self.raw_path.open("wb") as handle:
            while True:
                chunk = self.proc.stdout.read(4096)
                if not chunk:
                    break
                handle.write(chunk)
                handle.flush()
                with self.lock:
                    self.bytes_written += len(chunk)
                    if self.bytes_written >= MAX_RECORDING_BYTES:
                        self.logger.log(f"Recording reached {MAX_RECORDING_BYTES} byte limit, stopping")
                        break

    def _consume_stderr(self) -> None:
        assert self.proc is not None and self.proc.stderr is not None
        for raw_line in self.proc.stderr:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if line:
                self.logger.log(f"parec: {line}")

    def available(self) -> int:
        with self.lock:
            return self.bytes_written

    def stop(self) -> None:
        if self.proc is None:
            return
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=2)
        if self.stdout_thread is not None:
            self.stdout_thread.join(timeout=2)
        if self.stderr_thread is not None:
            self.stderr_thread.join(timeout=2)
        self.logger.log(f"Recorder stopped with {self.available()} bytes captured")

    def read_segment(self, start: int, end: int) -> bytes:
        end = min(end, self.available())
        if end <= start:
            return b""
        with self.raw_path.open("rb") as handle:
            handle.seek(start)
            return handle.read(end - start)

    def cleanup(self) -> None:
        try:
            self.raw_path.unlink()
        except FileNotFoundError:
            pass


class Transcriber(threading.Thread):
    def __init__(
        self,
        recorder: Recorder,
        whisper_cli: Path,
        model: Path,
        language: str,
        type_delay_ms: int,
        logger: Logger,
        live_type: bool = False,
        suppress_regex: str = "",
        suppress_nst: bool = True,
        smart_punctuation: bool = True,
        symbol_words_to_symbols: bool = False,
        direct_streaming: bool = False,
        faster_whisper_model: WhisperModel | None = None,
        inference_client: WhisperInferenceClient | None = None,
        on_text_typed: Callable[[str], None] | None = None,
    ):
        super().__init__(daemon=True)
        self.recorder = recorder
        self.whisper_cli = whisper_cli
        self.model = model
        self.language = language
        self.type_delay_ms = type_delay_ms
        self.logger = logger
        self.live_type = live_type
        self.suppress_regex = suppress_regex
        self.suppress_nst = suppress_nst
        self.smart_punctuation = smart_punctuation
        self.symbol_words_to_symbols = symbol_words_to_symbols
        self.direct_streaming = direct_streaming
        self._fw_model = faster_whisper_model
        self._inference_client = inference_client
        self._on_text_typed = on_text_typed
        self.jobs = queue.Queue(maxsize=8)
        self.history_words = []
        self.pending_fragments = []
        self.pending_lock = threading.Lock()
        self.typed_text = ""
        self.typed_lock = threading.Lock()
        self._needs_leading_space = False

    def enqueue(self, job: SegmentJob) -> None:
        self.jobs.put(job)

    def finish(self) -> None:
        self.jobs.put(None)

    def flush_pending_text(self) -> None:
        with self.pending_lock:
            payload = " ".join(self.pending_fragments).strip()
            self.pending_fragments.clear()
        if payload:
            payload = _deduplicate_flush_text(payload)
            if payload:
                self._type_text(payload)

    def run(self) -> None:
        while True:
            job = self.jobs.get()
            if job is None:
                return
            try:
                self._process(job)
            finally:
                self.jobs.task_done()

    def _process(self, job: SegmentJob) -> None:
        pcm_data = self.recorder.read_segment(job.start, job.end)
        if len(pcm_data) < int(BYTES_PER_SECOND * 0.25):
            self.logger.log(f"Skipping tiny segment {job.index}: {len(pcm_data)} bytes")
            return

        if self._inference_client is not None:
            self._process_inference_client(job, pcm_data)
            return

        if self._fw_model is not None:
            self._process_faster_whisper(job, pcm_data)
            return

        self._process_cli_fallback(job, pcm_data)

    def _process_faster_whisper(self, job: SegmentJob, pcm_data: bytes) -> None:
        audio_array = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0

        self.logger.log(f"Transcribing segment {job.index} with faster-whisper")
        try:
            segments, info = self._fw_model.transcribe(
                audio_array,
                vad_filter=True,
                vad_parameters=dict(threshold=0.5, min_speech_duration_ms=250, min_silence_duration_ms=500),
                word_timestamps=True,
                no_speech_threshold=0.7,
                compression_ratio_threshold=2.2,
                language=self.language,
            )
        except Exception as exc:
            self.logger.log(f"Segment {job.index}: faster-whisper transcribe failed: {exc}")
            return

        transcript_parts = []
        for segment in segments:
            if hasattr(segment, 'no_speech_prob') and segment.no_speech_prob > 0.7:
                continue
            if segment.text:
                transcript_parts.append(segment.text)

        transcript = " ".join(transcript_parts).strip()
        # Strip whisper-added punctuation (user says "period" for symbols)
        transcript = _STRIP_PUNCT_RE.sub("", transcript)
        self.logger.log(f"Segment {job.index} final={job.final} text={transcript!r}")

        if not transcript:
            return

        if self._is_silence_hallucination(transcript):
            self.logger.log(f"Segment {job.index}: filtered filler/hallucination")
            return

        append_text = compute_append_text(self.history_words, transcript)
        if not append_text:
            self.logger.log(f"Segment {job.index}: fully deduped, transcript was {transcript!r}, history tail={self.history_words[-6:]}")
            return

        if self.live_type or self.direct_streaming:
            self._type_text(append_text)
        else:
            self.logger.log(f"Buffered text chunk: {append_text!r}")
            with self.pending_lock:
                self.pending_fragments.append(append_text)
        self.history_words.extend(append_text.split())
        if len(self.history_words) > 64:
            self.history_words = self.history_words[-64:]

    def _process_inference_client(self, job: SegmentJob, pcm_data: bytes) -> None:
        self.logger.log(f"Transcribing segment {job.index} via Docker inference")
        transcript = self._inference_client.transcribe(pcm_data, self.language)
        if not transcript:
            self.logger.log(f"Segment {job.index}: empty transcript from inference client")
            return
        transcript = _STRIP_PUNCT_RE.sub("", transcript)
        self.logger.log(f"Segment {job.index} final={job.final} text={transcript!r}")
        if self._is_silence_hallucination(transcript):
            self.logger.log(f"Segment {job.index}: filtered filler/hallucination")
            return
        append_text = compute_append_text(self.history_words, transcript)
        if not append_text:
            self.logger.log(f"Segment {job.index}: fully deduped")
            return
        if self.live_type or self.direct_streaming:
            self._type_text(append_text)
        else:
            with self.pending_lock:
                self.pending_fragments.append(append_text)
        self.history_words.extend(append_text.split())
        if len(self.history_words) > 64:
            self.history_words = self.history_words[-64:]

    def _process_cli_fallback(self, job: SegmentJob, pcm_data: bytes) -> None:
        wav_fd, wav_path = tempfile.mkstemp(prefix=f"whisper_chunk_{job.index:03d}_", suffix=".wav")
        os.close(wav_fd)
        wav_file = Path(wav_path)
        try:
            with wave.open(str(wav_file), "wb") as handle:
                handle.setnchannels(CHANNELS)
                handle.setsampwidth(SAMPLE_WIDTH)
                handle.setframerate(SAMPLE_RATE)
                handle.writeframes(pcm_data)

            command = [
                str(self.whisper_cli),
                "-m",
                str(self.model),
                "-f",
                str(wav_file),
                "--no-timestamps",
                "--no-prints",
                "-l",
                self.language,
            ]
            if self.suppress_regex:
                command.extend(["--suppress-regex", self.suppress_regex])
            if self.suppress_nst:
                command.append("--suppress-nst")
            command.extend(["--no-speech-thold", "0.8"])
            command.extend(["--best-of", "8"])
            command.extend(["--entropy-thold", "2.8"])
            command.extend(["--max-context", "64"])
            self.logger.log(f"Transcribing segment {job.index}: {shell_join(command)}")
            try:
                result = subprocess.run(
                    command,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            except subprocess.TimeoutExpired:
                self.logger.log(f"Segment {job.index}: whisper-cli timed out after 30s")
                return
            transcript = clean_transcript((result.stdout or "") + "\n" + (result.stderr or ""))
            self.logger.log(
                f"Segment {job.index} exit={result.returncode} final={job.final} text={transcript!r}"
            )
            if result.returncode != 0 or not transcript:
                return

            if self._is_silence_hallucination(transcript):
                self.logger.log(f"Segment {job.index}: filtered silence hallucination")
                return

            if self._is_repetitive_hallucination(transcript):
                self.logger.log(f"Segment {job.index}: filtered repetitive hallucination")
                return

            append_text = compute_append_text(self.history_words, transcript)
            if not append_text:
                self.logger.log(f"Segment {job.index}: fully deduped, transcript={transcript!r}, history tail={self.history_words[-6:]}")
                return

            if self.live_type or self.direct_streaming:
                self._type_text(append_text)
            else:
                self.logger.log(f"Buffered text chunk: {append_text!r}")
                with self.pending_lock:
                    self.pending_fragments.append(append_text)
            self.history_words.extend(append_text.split())
            if len(self.history_words) > 64:
                self.history_words = self.history_words[-64:]
        finally:
            try:
                wav_file.unlink()
            except FileNotFoundError:
                pass

    def _deduplicate_text(self, new_text: str, already_typed: str) -> str:
        """Remove leading overlap with already_typed in streaming mode"""
        if not already_typed:
            return new_text

        new_words = new_text.split()
        already_words = already_typed.split()
        if not new_words:
            return ""

        tail = already_words[-12:] if len(already_words) >= 12 else already_words
        max_check = min(len(tail), len(new_words), 8)

        best_overlap = 0
        for overlap in range(max_check, 0, -1):
            match = all(
                tail[-overlap + j].lower() == new_words[j].lower()
                for j in range(overlap)
            )
            if match:
                best_overlap = overlap
                break

        if best_overlap > 0:
            self.logger.log(f"Dedup: stripped {best_overlap} overlapping words from {new_words[:best_overlap]!r}")
        return " ".join(new_words[best_overlap:])

    def _type_text(self, text: str) -> None:
        if not text:
            return

        processed_text = text.strip()
        processed_text = self._strip_non_speech_tokens(processed_text)
        if not processed_text:
            return

        if self._is_repetitive_hallucination(processed_text):
            self.logger.log(f"Suppressed repetitive hallucination: {processed_text[:80]!r}")
            return

        if self.direct_streaming:
            processed_text = self._fix_double_words(processed_text)
            processed_text = self._remove_ellipses(processed_text)
            processed_text = self._symbol_word_to_symbol(processed_text)

            with self.typed_lock:
                already_typed = self.typed_text
                processed_text = self._deduplicate_text(processed_text, already_typed)
                self.typed_text += " " + processed_text

            if not processed_text:
                return
        else:
            processed_text = self._process_smart_punctuation(processed_text)
            processed_text = self._fix_double_words(processed_text)
            processed_text = self._remove_ellipses(processed_text)
            processed_text = self._symbol_word_to_symbol(processed_text)

        payload = processed_text.rstrip()
        if not payload:
            return

        if self._needs_leading_space and not payload.startswith((" ", "\n")):
            if not payload[0:1] in ".,;:?!-":
                payload = " " + payload
        self._needs_leading_space = True

        command = [
            "xdotool",
            "type",
            "--clearmodifiers",
            "--delay",
            str(self.type_delay_ms),
            "--file",
            "-",
        ]
        self.logger.log(f"Typing text: {payload!r}")
        try:
            result = subprocess.run(command, input=payload, text=True, capture_output=True, check=False, timeout=10)
        except subprocess.TimeoutExpired:
            self.logger.log(f"xdotool timed out after 10s for payload: {payload!r}")
            return
        if result.returncode != 0:
            self.logger.log(f"xdotool exit={result.returncode} stderr={result.stderr.strip()!r}")
        else:
            if self._on_text_typed:
                self._on_text_typed(payload)

    def _is_punctuation_word(self, word: str) -> bool:
        punctuation_words = {
            "comma", "period", "dot", "point", "question",
            "question mark", "exclamation", "exclamation mark",
            "colon", "semicolon", "hyphen", "dash",
        }
        return word.lower() in punctuation_words

    _STRIP_TRAILING_PUNCT = re.compile(r"[,.?!;:]+$")
    _SYMBOL_FOLLOW_WORDS = frozenset({"mark", "marks"})

    def _symbol_word_to_symbol(self, text: str) -> str:
        if not self.symbol_words_to_symbols:
            return text
        symbol_map = {
            "comma": ",", "period": ".", "dot": ".", "point": ".",
            "question mark": "?", "question": "?",
            "exclamation mark": "!", "exclamation": "!",
            "colon": ":", "semicolon": ";",
            "hyphen": "-", "dash": "-",
            "pew": ".", "pearl": ".", "pear": ".", "peer": ".",
            "pier": ".", "pur": ".", "pure": ".",
            "coma": ",", "karma": ",", "comer": ",",
            "semi colon": ";", "semi": ";",
        }
        raw_words = text.split()
        words = [self._STRIP_TRAILING_PUNCT.sub("", w) for w in raw_words]
        result = []
        i = 0
        while i < len(words):
            w = words[i]
            if not w:
                i += 1
                continue
            lower_word = w.lower()
            two_word = f"{lower_word} {words[i + 1].lower()}" if i + 1 < len(words) else ""
            if two_word in symbol_map:
                symbol = symbol_map[two_word]
                if result:
                    result[-1] = result[-1] + symbol
                else:
                    result.append(symbol)
                i += 2
            elif lower_word in symbol_map:
                symbol = symbol_map[lower_word]
                if result:
                    result[-1] = result[-1] + symbol
                else:
                    result.append(symbol)
                i += 1
            else:
                result.append(raw_words[i])
                i += 1
        return " ".join(result)

    def _process_smart_punctuation(self, text: str) -> str:
        if not self.smart_punctuation:
            return text
        words = text.split()
        result = []
        i = 0
        while i < len(words):
            word = words[i]
            if self._is_punctuation_word(word):
                result.append(word)
                i += 1
                continue
            if word in ",.!?;:":
                if i + 1 < len(words):
                    next_word = words[i + 1]
                    if not self._is_punctuation_word(next_word) and next_word not in ",.!?;:":
                        i += 1
                        continue
                result.append(word)
                i += 1
            else:
                result.append(word)
                i += 1
        return " ".join(result)

    def _fix_double_words(self, text: str) -> str:
        result = re.sub(r"\bellipsis\b", "ellipses", text, flags=re.IGNORECASE)
        result = re.sub(r"\blip-sync\w+", "lip-sync", result, flags=re.IGNORECASE)
        result = re.sub(r"\bthe the\b", "the", result, flags=re.IGNORECASE)
        result = re.sub(r"\ba a\b", "a", result, flags=re.IGNORECASE)
        return result

    def _remove_ellipses(self, text: str) -> str:
        result = re.sub(r"\.{2,}", "", text)
        return result.strip()

    _NON_SPEECH_PATTERN = re.compile(r"[♪♩♫♬♭♮♯\u266a-\u266f\u2669]+")

    def _strip_non_speech_tokens(self, text: str) -> str:
        result = self._NON_SPEECH_PATTERN.sub("", text)
        return result.strip()

    _SILENCE_HALLUCINATION_WORDS = frozenset({
        "you", "yeah", "uh", "um", "mm", "hmm", "mmm", "hm",
        "shh", "shh!", "shh.", "hmm!", "hmm.",
    })

    _SILENCE_HALLUCINATION_PHRASES = [
        "thank you for watching",
        "thank you for listening",
        "thank you very much",
        "subscribe to my channel",
        "like and subscribe",
        "please subscribe",
    ]

    def _is_silence_hallucination(self, text: str) -> bool:
        stripped = text.lower().strip()
        words = stripped.split()
        if len(words) > 6:
            return False
        if any(p in stripped for p in self._SILENCE_HALLUCINATION_PHRASES):
            return True
        if len(words) <= 2:
            return all(w in self._SILENCE_HALLUCINATION_WORDS for w in words)
        return False

    def _is_repetitive_hallucination(self, text: str) -> bool:
        words = text.lower().split()
        if len(words) < 8:
            return False
        for phrase_len in range(3, min(12, len(words) // 3) + 1):
            for start in range(min(4, len(words) - phrase_len * 3)):
                phrase = " ".join(words[start:start + phrase_len])
                count = text.lower().count(phrase)
                if count >= 3:
                    return True
        return False


class X11HotkeyDaemon:
    def __init__(
        self,
        source: str,
        whisper_cli: Path,
        model: Path,
        language: str,
        chunk_seconds: float,
        overlap_seconds: float,
        type_delay_ms: int,
        logger: Logger,
        suppress_regex: str = "",
        suppress_nst: bool = True,
        smart_punctuation: bool = True,
        symbol_words_to_symbols: bool = False,
        direct_streaming: bool = False,
        activation_mode: str = "hold",
        indicator: bool = True,
        faster_whisper_model: WhisperModel | None = None,
        inference_client: WhisperInferenceClient | None = None,
        postprocess_enabled: bool = False,
        postprocess_mode: str = "off",
        postprocess_trigger: str = "manual",
    ):
        self.source = source
        self.whisper_cli = whisper_cli
        self.model = model
        self.language = language
        self.chunk_bytes = max(int(chunk_seconds * BYTES_PER_SECOND), int(BYTES_PER_SECOND * 0.75))
        self.overlap_bytes = max(0, int(overlap_seconds * BYTES_PER_SECOND))
        self.type_delay_ms = type_delay_ms
        self.logger = logger
        self.suppress_regex = suppress_regex
        self.suppress_nst = suppress_nst
        self.smart_punctuation = smart_punctuation
        self.symbol_words_to_symbols = symbol_words_to_symbols
        self.direct_streaming = direct_streaming
        self.activation_mode = activation_mode
        self.indicator = indicator
        self._fw_model = faster_whisper_model
        self._inference_client = inference_client
        self._postprocessing_enabled = postprocess_enabled
        self._postprocessing_mode = postprocess_mode if postprocess_mode != "off" else "off"
        self._postprocessing_trigger = postprocess_trigger
        self.running = True
        self.recording_active = False
        self.display = None
        self.root = None
        self._caret_tracker = None
        self.space_keycode = None
        self.control_left_keycode = None
        self.control_right_keycode = None
        self.shift_left_keycode = None
        self.shift_right_keycode = None
        self.m_keycode = None
        self.numlock_mask = 0
        self.libx11 = ctypes.cdll.LoadLibrary("libX11.so.6")
        self._setup_xlib()
        self._session_text = ""
        self._postprocessor = PostProcessor(
            mode=PostProcessMode(postprocess_mode),
            trigger=PostProcessTrigger(postprocess_trigger),
        )

    def _setup_xlib(self) -> None:
        self.libx11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        self.libx11.XOpenDisplay.restype = ctypes.c_void_p
        self.libx11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        self.libx11.XDefaultRootWindow.restype = ctypes.c_ulong
        self.libx11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        self.libx11.XKeysymToKeycode.restype = ctypes.c_uint
        self.libx11.XGrabKey.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_uint,
            ctypes.c_ulong,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        ]
        self.libx11.XUngrabKey.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_uint,
            ctypes.c_ulong,
        ]
        self.libx11.XNextEvent.argtypes = [ctypes.c_void_p, ctypes.POINTER(XEvent)]
        self.libx11.XQueryKeymap.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_char)]
        self.libx11.XGetModifierMapping.argtypes = [ctypes.c_void_p]
        self.libx11.XGetModifierMapping.restype = ctypes.c_void_p
        self.libx11.XFreeModifiermap.argtypes = [ctypes.c_void_p]
        self.libx11.XPending.argtypes = [ctypes.c_void_p]
        self.libx11.XPending.restype = ctypes.c_int
        self.libx11.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.libx11.XCloseDisplay.argtypes = [ctypes.c_void_p]

    def open(self) -> None:
        display_name = os.environ.get("DISPLAY")
        if not display_name:
            raise RuntimeError("DISPLAY is not set; this daemon requires an X11 session")

        self.display = self.libx11.XOpenDisplay(display_name.encode("utf-8"))
        if not self.display:
            raise RuntimeError(f"unable to open X display {display_name}")

        self.root = self.libx11.XDefaultRootWindow(self.display)
        self.space_keycode = self.libx11.XKeysymToKeycode(self.display, XK_SPACE)
        self.control_left_keycode = self.libx11.XKeysymToKeycode(self.display, XK_CONTROL_L)
        self.control_right_keycode = self.libx11.XKeysymToKeycode(self.display, XK_CONTROL_R)
        self.shift_left_keycode = self.libx11.XKeysymToKeycode(self.display, XK_SHIFT_L)
        self.shift_right_keycode = self.libx11.XKeysymToKeycode(self.display, XK_SHIFT_R)
        self.m_keycode = self.libx11.XKeysymToKeycode(self.display, XK_M)
        self.numlock_mask = self._detect_numlock_mask()
        self.logger.log(
            f"Connected to X11 display={display_name} space={self.space_keycode} ctrl_l={self.control_left_keycode} ctrl_r={self.control_right_keycode} numlock_mask={self.numlock_mask:#x}"
        )

        self._indicator = None
        if self.indicator:
            try:
                from whisper_hotkey.indicator import CaretTracker, CursorIndicator
                self._caret_tracker = CaretTracker(logger=self.logger)
                self._caret_tracker.start()
                self._indicator = CursorIndicator(
                    libx11=self.libx11,
                    display=self.display,
                    root_window=self.root,
                    logger=self.logger,
                    caret_tracker=self._caret_tracker,
                )
            except Exception as exc:
                self.logger.log(f"CursorIndicator init failed: {exc}")
                self._indicator = None

    def _detect_numlock_mask(self) -> int:
        class XModifierKeymap(ctypes.Structure):
            _fields_ = [
                ("max_keypermod", ctypes.c_int),
                ("modifiermap", ctypes.POINTER(ctypes.c_ubyte)),
            ]

        modifier_map_ptr = self.libx11.XGetModifierMapping(self.display)
        if not modifier_map_ptr:
            return 0
        try:
            modifier_map = ctypes.cast(modifier_map_ptr, ctypes.POINTER(XModifierKeymap)).contents
            numlock_keycode = self.libx11.XKeysymToKeycode(self.display, XK_NUM_LOCK)
            for mod_index in range(8):
                for key_index in range(modifier_map.max_keypermod):
                    keycode = modifier_map.modifiermap[mod_index * modifier_map.max_keypermod + key_index]
                    if keycode == numlock_keycode:
                        return 1 << mod_index
        finally:
            self.libx11.XFreeModifiermap(modifier_map_ptr)
        return 0

    def grab(self) -> None:
        modifier_variants = {CONTROL_MASK}
        for extra_mask in (LOCK_MASK, self.numlock_mask, MOD2_MASK, MOD5_MASK):
            if extra_mask:
                modifier_variants.update({CONTROL_MASK | extra_mask, CONTROL_MASK | LOCK_MASK | extra_mask})
        for modifiers in modifier_variants:
            self.libx11.XGrabKey(
                self.display,
                int(self.space_keycode),
                modifiers,
                self.root,
                0,
                GRAB_MODE_ASYNC,
                GRAB_MODE_ASYNC,
            )
        self.libx11.XSync(self.display, 0)
        self.logger.log("Ctrl+Space key grab registered")

        # Mode cycling: Ctrl+Shift+Alt+Space
        mode_modifiers_base = CONTROL_MASK | SHIFT_MASK | MOD1_MASK
        mode_modifier_variants = {mode_modifiers_base}
        for extra_mask in (LOCK_MASK, self.numlock_mask, MOD2_MASK, MOD5_MASK):
            if extra_mask:
                mode_modifier_variants.update({mode_modifiers_base | extra_mask, mode_modifiers_base | LOCK_MASK | extra_mask})
        for modifiers in mode_modifier_variants:
            self.libx11.XGrabKey(
                self.display,
                int(self.space_keycode),
                modifiers,
                self.root,
                0,
                GRAB_MODE_ASYNC,
                GRAB_MODE_ASYNC,
            )
        self.libx11.XSync(self.display, 0)
        self.logger.log("Ctrl+Shift+Alt+Space mode cycling key grab registered")

    def ungrab(self) -> None:
        if not self.display:
            return
        modifier_variants = {CONTROL_MASK}
        for extra_mask in (LOCK_MASK, self.numlock_mask, MOD2_MASK, MOD5_MASK):
            if extra_mask:
                modifier_variants.update({CONTROL_MASK | extra_mask, CONTROL_MASK | LOCK_MASK | extra_mask})
        for modifiers in modifier_variants:
            self.libx11.XUngrabKey(self.display, int(self.space_keycode), modifiers, self.root)
        self.libx11.XSync(self.display, 0)

    def close(self) -> None:
        if self.display:
            if self._indicator:
                self._indicator.destroy()
                self._indicator = None
            if self._caret_tracker:
                self._caret_tracker.stop()
                self._caret_tracker = None
            if hasattr(self, '_recorder') and self._recorder:
                self._recorder.stop()
                self._recorder.cleanup()
            if hasattr(self, '_inference_client') and self._inference_client:
                self._inference_client.close()
            self.ungrab()
            self.libx11.XCloseDisplay(self.display)
            self.display = None

    def stop(self, *_args) -> None:
        self.running = False
        self.logger.log("Shutdown requested")

    def is_hotkey_held(self) -> bool:
        keymap = ctypes.create_string_buffer(32)
        self.libx11.XQueryKeymap(self.display, keymap)

        def is_pressed(keycode: int) -> bool:
            return bool(keymap.raw[keycode // 8] & (1 << (keycode % 8)))

        space_down = is_pressed(self.space_keycode)
        control_down = is_pressed(self.control_left_keycode) or is_pressed(self.control_right_keycode)
        return space_down and control_down

    def _on_text_typed(self, text: str) -> None:
        if not self._postprocessing_enabled:
            return
        self._session_text += "  " + text

    def _reset_session_text(self) -> None:
        self._session_text = ""

    def _run_postprocessing(self) -> None:
        if not self._postprocessing_enabled or not self._session_text.strip():
            return

        if not self._postprocessor.should_process(self._session_text):
            return

        self.logger.log(f"Running post-processing on session text ({len(self._session_text)} chars): {self._postprocessing_mode}")

        processed = self._postprocessor.process(self._session_text)

        if processed != self._session_text:
            self.logger.log(f"Post-processing complete. Diff: {processed[:50]}...")
            subprocess.run(["xdotool", "type", processed], check=True, timeout=5)
        else:
            self.logger.log("Post-processing: no changes made")

    def _cycle_postprocess_mode(self) -> None:
        modes = [
            PostProcessMode.OFF,
            PostProcessMode.LIGHT,
            PostProcessMode.AGGRESSIVE,
            PostProcessMode.AGENTIC,
            PostProcessMode.WRITING,
            PostProcessMode.CODE,
            PostProcessMode.STRUCTURE,
            PostProcessMode.PERSONA,
            PostProcessMode.CLARITY,
        ]

        try:
            current_index = modes.index(self._postprocessor.mode)
            new_index = (current_index + 1) % len(modes)
        except ValueError:
            new_index = 0

        new_mode = modes[new_index]
        self._postprocessor = PostProcessor(
            mode=new_mode,
            trigger=self._postprocessor.trigger,
        )
        self._postprocessing_mode = new_mode.value
        self.logger.log(f"Post-processing mode changed: {new_mode.value}")

        toast_text = f"Grammar mode: {new_mode.value}"
        try:
            subprocess.run(
                ["notify-send", "Whisper Hotkey", toast_text],
                check=True,
                capture_output=True,
                timeout=5,
            )
        except Exception:
            print(f"[{toast_text}]")

    def drain_pending_events(self) -> None:
        event = XEvent()
        count = 0
        while self.libx11.XPending(self.display) > 0 and count < 50:
            self.libx11.XNextEvent(self.display, ctypes.byref(event))
            count += 1

    def _cleanup_stale_temp_files(self) -> None:
        import glob
        for path in glob.glob("/tmp/whisper_stream_*.s16le"):
            try:
                Path(path).unlink()
                self.logger.log(f"Cleaned up stale temp file: {path}")
            except Exception:
                pass

    def run(self) -> None:
        self.open()
        self._cleanup_stale_temp_files()
        self.grab()
        mode_label = "toggle" if self.activation_mode == "toggle" else "hold"
        print(f"Whisper Ctrl+Space daemon is listening. Mode: {mode_label}.")
        print(f"Model: {self.model}")
        print(f"Source: {self.source}")
        print(f"Log: {self.logger.path}")
        self.logger.log(f"Daemon ready mode={mode_label} model={self.model} source={self.source}")

        event = XEvent()
        while self.running:
            if self.libx11.XPending(self.display) == 0:
                time.sleep(0.05)
                continue

            self.libx11.XNextEvent(self.display, ctypes.byref(event))
            if not self.running:
                break

            if event.type == FOCUS_OUT and self.recording_active:
                self.logger.log("FocusOut detected; stopping recording")
                if self.activation_mode == "toggle":
                    self.handle_toggle_session()
                else:
                    self.handle_hold_release()
                continue

            if event.type != KEY_PRESS:
                continue

            if event.xkey.keycode == self.space_keycode and (event.xkey.state & (CONTROL_MASK | SHIFT_MASK | MOD1_MASK)) == (CONTROL_MASK | SHIFT_MASK | MOD1_MASK):
                self.logger.log("Ctrl+Shift+Alt+Space pressed; cycling post-processing mode")
                self._cycle_postprocess_mode()
                self.drain_pending_events()
                continue

            if event.xkey.keycode != self.space_keycode:
                continue
            if (event.xkey.state & CONTROL_MASK) == 0:
                continue

            if self.activation_mode == "toggle":
                if self.recording_active:
                    self.logger.log("Ctrl+Space pressed; stopping toggle session")
                else:
                    self.logger.log("Ctrl+Space pressed; starting toggle session")
                self.handle_toggle_session()
            else:
                self.logger.log("Ctrl+Space pressed; starting hold session")
                self.handle_hold_session()
            self.drain_pending_events()

    def handle_toggle_session(self) -> None:
        if self.recording_active:
            self.recording_active = False
            if self._indicator:
                self._indicator.hide()
            if hasattr(self, "_recorder") and self._recorder:
                time.sleep(0.5)
                self._recorder.stop()
                available = self._recorder.available()
                final_start = max(0, available - self.chunk_bytes)
                if available > final_start:
                    self._transcriber.enqueue(
                        SegmentJob(index=self._segment_index, start=final_start, end=available, final=True)
                    )
                self._transcriber.finish()
                self._transcriber.join()
                self._transcriber.flush_pending_text()
                self._run_postprocessing()
                self._recorder.cleanup()
                self.logger.log("Toggle session stopped; text flushed")
                print("Recording stopped.")
                self._recorder = None
                self._transcriber = None
            return

        # Before creating new Recorder, ensure any previous session is fully cleaned up
        if self._recorder is not None:
            self.logger.log("Warning: previous recorder still exists, cleaning up")
            try:
                self._recorder.stop()
                self._recorder.cleanup()
            except Exception:
                pass
            self._recorder = None
        if self._transcriber is not None:
            self.logger.log("Warning: previous transcriber still exists, cleaning up")
            try:
                self._transcriber.finish()
                self._transcriber.join(timeout=2)
            except Exception:
                pass
            self._transcriber = None

        self.recording_active = True
        self._recorder = Recorder(self.source, self.logger)
        self._transcriber = Transcriber(
            recorder=self._recorder,
            whisper_cli=self.whisper_cli,
            model=self.model,
            language=self.language,
            type_delay_ms=self.type_delay_ms,
            logger=self.logger,
            live_type=True,
            suppress_regex=self.suppress_regex,
            suppress_nst=self.suppress_nst,
            smart_punctuation=self.smart_punctuation,
            symbol_words_to_symbols=self.symbol_words_to_symbols,
            direct_streaming=self.direct_streaming,
            faster_whisper_model=self._fw_model,
            on_text_typed=self._on_text_typed,
        )
        self._next_chunk_end = self.chunk_bytes
        self._segment_index = 0
        self._reset_session_text()
        self._recorder.start()
        self._transcriber.start()
        if self._indicator:
            self._indicator.show()
        print("Recording... press Ctrl+Space again to stop.")

        while self.running and self.recording_active:
            event = XEvent()
            count = 0
            while self.libx11.XPending(self.display) > 0 and count < 20:
                self.libx11.XNextEvent(self.display, ctypes.byref(event))
                count += 1
                if event.type == KEY_PRESS and event.xkey.keycode == self.space_keycode:
                    if (event.xkey.state & CONTROL_MASK) != 0:
                        self.logger.log("Ctrl+Space pressed; toggling off")
                        self.recording_active = False
                        break

            available = self._recorder.available()
            while available >= self._next_chunk_end:
                start = max(0, self._next_chunk_end - self.chunk_bytes - self.overlap_bytes)
                self._transcriber.enqueue(
                    SegmentJob(index=self._segment_index, start=start, end=self._next_chunk_end, final=False)
                )
                self._segment_index += 1
                self._next_chunk_end += self.chunk_bytes
            if self._indicator:
                self._indicator.tick()
            time.sleep(0.05)

        # Always hide indicator and stop recording when loop exits
        self.recording_active = False
        if self._indicator:
            self._indicator.hide()

        # Trailing buffer: wait 500ms to capture last words
        time.sleep(0.5)
        # Enqueue final segment with whatever audio remains
        available = self._recorder.available()
        if available > int(BYTES_PER_SECOND * 0.25):
            start = max(0, self._next_chunk_end - self.chunk_bytes - self.overlap_bytes)
            self._transcriber.enqueue(
                SegmentJob(index=self._segment_index, start=start, end=available, final=True)
            )
            self.logger.log(f"Final segment {self._segment_index} queued: {start}-{available}")

    def handle_hold_session(self) -> None:
        recorder = Recorder(self.source, self.logger)
        transcriber = Transcriber(
            recorder=recorder,
            whisper_cli=self.whisper_cli,
            model=self.model,
            language=self.language,
            type_delay_ms=self.type_delay_ms,
            logger=self.logger,
            live_type=True,
            suppress_regex=self.suppress_regex,
            suppress_nst=self.suppress_nst,
            smart_punctuation=self.smart_punctuation,
            symbol_words_to_symbols=self.symbol_words_to_symbols,
            direct_streaming=self.direct_streaming,
            faster_whisper_model=self._fw_model,
            inference_client=self._inference_client,
            on_text_typed=self._on_text_typed,
        )

        next_chunk_end = self.chunk_bytes
        segment_index = 0
        self._reset_session_text()
        recorder.start()
        transcriber.start()
        if self._indicator:
            self._indicator.show()
        session_start = time.monotonic()
        released_since = None
        print("Recording... release Ctrl+Space to stop.")

        try:
            key_released = False
            while self.running and not key_released:
                # Use event-driven KeyRelease detection instead of XQueryKeymap.
                # xdotool keystrokes during streaming cause XQueryKeymap to
                # report grab key as released even while physically held.
                released_since = None
                event = XEvent()
                count = 0
                while self.libx11.XPending(self.display) > 0 and count < 20:
                    self.libx11.XNextEvent(self.display, ctypes.byref(event))
                    count += 1
                    if event.type == FOCUS_OUT:
                        self.logger.log("FocusOut detected during hold session; stopping")
                        key_released = True
                        break
                    if event.type == KEY_RELEASE:
                        if (event.xkey.keycode == self.space_keycode
                                or event.xkey.keycode == self.control_left_keycode
                                or event.xkey.keycode == self.control_right_keycode):
                            if released_since is None:
                                released_since = time.monotonic()
                            elif time.monotonic() - released_since >= RELEASE_GRACE_SECONDS:
                                key_released = True
                                break
                    elif event.type == KEY_PRESS:
                        if (event.xkey.keycode == self.space_keycode
                                and (event.xkey.state & CONTROL_MASK) != 0):
                            released_since = None
                if key_released:
                    break

                # XQueryKeymap fallback: only when the X queue is empty
                if not self.is_hotkey_held():
                    if released_since is None:
                        released_since = time.monotonic()
                    elif time.monotonic() - released_since >= RELEASE_GRACE_SECONDS:
                        break

                available = recorder.available()
                while available >= next_chunk_end:
                    start = max(0, next_chunk_end - self.chunk_bytes - self.overlap_bytes)
                    transcriber.enqueue(
                        SegmentJob(index=segment_index, start=start, end=next_chunk_end, final=False)
                    )
                    segment_index += 1
                    next_chunk_end += self.chunk_bytes
                if self._indicator:
                    self._indicator.tick()
                time.sleep(0.05)

            recorder.stop()
            available = recorder.available()
            final_start = max(0, next_chunk_end - self.chunk_bytes - self.overlap_bytes)
            if available > final_start:
                transcriber.enqueue(
                    SegmentJob(index=segment_index, start=final_start, end=available, final=True)
                )
            transcriber.finish()
            transcriber.join()
            # Delay text injection until after release; typing during the hold can
            # interfere with the pressed-state check for Ctrl+Space.
            transcriber.flush_pending_text()
            if self._indicator:
                self._indicator.hide()
            session_duration = time.monotonic() - session_start
            self.logger.log(f"Hold session finished after {session_duration:.2f}s")
            self._run_postprocessing()
            print("Ready for the next Ctrl+Space hold.")
        finally:
            recorder.cleanup()


def run_once(
    whisper_cli: Path,
    model: Path,
    source: str,
    duration_seconds: float,
    language: str,
    type_delay_ms: int,
    logger: Logger,
    suppress_regex: str = "",
    suppress_nst: bool = True,
    smart_punctuation: bool = True,
    symbol_words_to_symbols: bool = False,
    direct_streaming: bool = False,
    faster_whisper_model: WhisperModel | None = None,
    inference_client: WhisperInferenceClient | None = None,
) -> int:
    logger.log(f"Running one-shot test for {duration_seconds:.2f}s")
    recorder = Recorder(source, logger)
    recorder.start()
    time.sleep(duration_seconds)
    recorder.stop()

    transcriber = Transcriber(
        recorder,
        whisper_cli,
        model,
        language,
        type_delay_ms,
        logger,
        live_type=True,
        suppress_regex=suppress_regex,
        suppress_nst=suppress_nst,
        smart_punctuation=smart_punctuation,
        symbol_words_to_symbols=symbol_words_to_symbols,
        direct_streaming=direct_streaming,
        faster_whisper_model=faster_whisper_model,
        inference_client=inference_client,
    )
    transcriber.start()
    transcriber.enqueue(SegmentJob(index=0, start=0, end=recorder.available(), final=True))
    transcriber.finish()
    transcriber.join()
    recorder.cleanup()
    return 0


def ensure_dependencies(model: Path, whisper_cli: Path) -> None:
    if not whisper_cli.is_file():
        raise RuntimeError(f"whisper-cli not found: {whisper_cli}")
    if not model.is_file():
        raise RuntimeError(f"model not found: {model}")
    for command in ("parec", "pactl", "xdotool"):
        if not shutil_which(command):
            raise RuntimeError(f"required command not found: {command}")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    logger = Logger(Path(args.log_file).expanduser())
    whisper_cli = Path(args.whisper_cli).expanduser()
    model = Path(args.model).expanduser()
    preferred_sources = parse_preferred_sources(args.preferred_sources)

    fw_model = None
    if HAS_FASTER_WHISPER:
        try:
            fw_model = WhisperModel("base.en", device="cpu", compute_type="int8",
                                  download_root=os.path.expanduser("~/.config/com.pais.handy/models/"))
            logger.log("faster-whisper model loaded (base.en, CPU, int8)")
        except Exception as e:
            logger.log(f"faster-whisper load failed: {e}, falling back to CLI")

    try:
        ensure_dependencies(model, whisper_cli)
        source = resolve_audio_source_with_retry(args.source, preferred_sources, logger)

        inference_client = None
        socket_path = os.path.join(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"), "whisper", "whisper.sock")
        if os.path.exists(socket_path):
            try:
                inference_client = WhisperInferenceClient(socket_path=socket_path)
                result = inference_client.ping()
                if result:
                    logger.log(f"Docker inference client connected: {result}")
                else:
                    logger.log("Docker inference ping failed, falling back")
                    inference_client = None
            except Exception as e:
                logger.log(f"Docker inference client failed: {e}")
                inference_client = None
        else:
            logger.log("No Docker inference socket found, using local inference")

        if args.test is not None:
            return run_once(
                whisper_cli=whisper_cli,
                model=model,
                source=source,
                duration_seconds=float(args.test),
                language=args.language,
                type_delay_ms=args.type_delay_ms,
                logger=logger,
                suppress_regex=args.suppress_regex,
                suppress_nst=args.suppress_nst,
                smart_punctuation=args.smart_punctuation,
                symbol_words_to_symbols=args.symbol_words_to_symbols,
                direct_streaming=args.direct_streaming,
                faster_whisper_model=fw_model,
                inference_client=inference_client,
            )

        instance = SingleInstance(LOCK_FILE)
        instance.acquire()
        daemon = X11HotkeyDaemon(
            source=source,
            whisper_cli=whisper_cli,
            model=model,
            language=args.language,
            chunk_seconds=args.chunk_seconds,
            overlap_seconds=args.overlap_seconds,
            type_delay_ms=args.type_delay_ms,
            logger=logger,
            suppress_regex=args.suppress_regex,
            suppress_nst=args.suppress_nst,
            smart_punctuation=args.smart_punctuation,
            symbol_words_to_symbols=args.symbol_words_to_symbols,
            direct_streaming=args.direct_streaming,
            activation_mode=args.activation_mode,
            indicator=args.indicator,
            faster_whisper_model=fw_model,
            inference_client=inference_client,
            postprocess_enabled=args.postprocess,
            postprocess_mode=args.postprocess_mode,
            postprocess_trigger=args.postprocess_trigger,
        )
        signal.signal(signal.SIGINT, daemon.stop)
        signal.signal(signal.SIGTERM, daemon.stop)
        try:
            daemon.run()
        finally:
            daemon.close()
        return 0
    except Exception as exc:
        logger.log(f"Fatal error: {exc}")
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
