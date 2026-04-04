import argparse
import ctypes
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
RELEASE_GRACE_SECONDS = 0.75

SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2
BYTES_PER_SECOND = SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH

KEY_PRESS = 2
GRAB_MODE_ASYNC = 1
CONTROL_MASK = 0x4
LOCK_MASK = 0x2
MOD2_MASK = 0x10
MOD5_MASK = 0x80
XK_SPACE = 0x20
XK_CONTROL_L = 0xFFE3
XK_CONTROL_R = 0xFFE4
XK_NUM_LOCK = 0xFF7F


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
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line)


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
        default=float(os.environ.get("WHISPER_CHUNK_SECONDS", "1.8")),
    )
    parser.add_argument(
        "--overlap-seconds",
        type=float,
        default=float(os.environ.get("WHISPER_OVERLAP_SECONDS", "0.4")),
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

    normalized_history = [normalize_token(word) for word in history_words[-24:]]
    normalized_new = [normalize_token(word) for word in new_words]

    best_overlap = 0
    max_overlap = min(len(normalized_history), len(normalized_new), 12)
    for overlap in range(max_overlap, 0, -1):
        if normalized_history[-overlap:] == normalized_new[:overlap]:
            best_overlap = overlap
            break

    append_words = new_words[best_overlap:]
    return " ".join(append_words).strip()


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
    ):
        super().__init__(daemon=True)
        self.recorder = recorder
        self.whisper_cli = whisper_cli
        self.model = model
        self.language = language
        self.type_delay_ms = type_delay_ms
        self.logger = logger
        self.live_type = live_type
        self.jobs = queue.Queue()
        self.history_words = []
        self.pending_fragments = []
        self.pending_lock = threading.Lock()

    def enqueue(self, job: SegmentJob) -> None:
        self.jobs.put(job)

    def finish(self) -> None:
        self.jobs.put(None)

    def flush_pending_text(self) -> None:
        with self.pending_lock:
            payload = " ".join(self.pending_fragments).strip()
            self.pending_fragments.clear()
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
            self.logger.log(f"Transcribing segment {job.index}: {shell_join(command)}")
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
            transcript = clean_transcript((result.stdout or "") + "\n" + (result.stderr or ""))
            self.logger.log(
                f"Segment {job.index} exit={result.returncode} final={job.final} text={transcript!r}"
            )
            if result.returncode != 0 or not transcript:
                return

            append_text = compute_append_text(self.history_words, transcript)
            if not append_text:
                return

            if self.live_type:
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

    def _type_text(self, text: str) -> None:
        payload = text if text.endswith(" ") else f"{text} "
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
        result = subprocess.run(command, input=payload, text=True, capture_output=True, check=False)
        if result.returncode != 0:
            self.logger.log(f"xdotool exit={result.returncode} stderr={result.stderr.strip()!r}")


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
    ):
        self.source = source
        self.whisper_cli = whisper_cli
        self.model = model
        self.language = language
        self.chunk_bytes = max(int(chunk_seconds * BYTES_PER_SECOND), int(BYTES_PER_SECOND * 0.75))
        self.overlap_bytes = max(0, int(overlap_seconds * BYTES_PER_SECOND))
        self.type_delay_ms = type_delay_ms
        self.logger = logger
        self.running = True
        self.display = None
        self.root = None
        self.space_keycode = None
        self.control_left_keycode = None
        self.control_right_keycode = None
        self.numlock_mask = 0
        self.libx11 = ctypes.cdll.LoadLibrary("libX11.so.6")
        self._setup_xlib()

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
        self.numlock_mask = self._detect_numlock_mask()
        self.logger.log(
            f"Connected to X11 display={display_name} space={self.space_keycode} ctrl_l={self.control_left_keycode} ctrl_r={self.control_right_keycode} numlock_mask={self.numlock_mask:#x}"
        )

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

    def drain_pending_events(self) -> None:
        event = XEvent()
        while self.libx11.XPending(self.display) > 0:
            self.libx11.XNextEvent(self.display, ctypes.byref(event))

    def run(self) -> None:
        self.open()
        self.grab()
        print("Whisper Ctrl+Space daemon is listening. Keep this running and hold Ctrl+Space to dictate.")
        print(f"Model: {self.model}")
        print(f"Source: {self.source}")
        print(f"Log: {self.logger.path}")
        self.logger.log(f"Daemon ready with model={self.model} source={self.source}")

        event = XEvent()
        while self.running:
            if self.libx11.XPending(self.display) == 0:
                time.sleep(0.05)
                continue

            self.libx11.XNextEvent(self.display, ctypes.byref(event))
            if not self.running:
                break
            if event.type != KEY_PRESS:
                continue
            if event.xkey.keycode != self.space_keycode:
                continue
            if (event.xkey.state & CONTROL_MASK) == 0:
                continue

            self.logger.log("Ctrl+Space pressed; starting hold session")
            self.handle_hold_session()
            self.drain_pending_events()

    def handle_hold_session(self) -> None:
        recorder = Recorder(self.source, self.logger)
        transcriber = Transcriber(
            recorder=recorder,
            whisper_cli=self.whisper_cli,
            model=self.model,
            language=self.language,
            type_delay_ms=self.type_delay_ms,
            logger=self.logger,
        )

        next_chunk_end = self.chunk_bytes
        segment_index = 0
        recorder.start()
        transcriber.start()
        session_start = time.monotonic()
        released_since = None
        print("Recording... release Ctrl+Space to stop.")

        try:
            while self.running:
                if self.is_hotkey_held():
                    released_since = None
                else:
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
            session_duration = time.monotonic() - session_start
            self.logger.log(f"Hold session finished after {session_duration:.2f}s")
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

    try:
        ensure_dependencies(model, whisper_cli)
        source = resolve_audio_source(args.source, preferred_sources, logger)
        if args.test is not None:
            return run_once(
                whisper_cli=whisper_cli,
                model=model,
                source=source,
                duration_seconds=float(args.test),
                language=args.language,
                type_delay_ms=args.type_delay_ms,
                logger=logger,
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
