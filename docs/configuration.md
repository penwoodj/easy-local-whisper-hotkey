# Configuration

`easy-local-whisper-hotkey` reads configuration from CLI flags first, then environment variables, then built-in defaults.

## Inference Mode

The tool supports two inference modes:

1. **Docker inference** (default) — connects to a `faster-whisper` server via Unix socket
2. **Native inference** (fallback) — calls `whisper-cli` from `whisper.cpp` directly

If a socket is found at `$XDG_RUNTIME_DIR/whisper/whisper.sock`, Docker inference is used automatically. Otherwise, native `whisper-cli` is attempted.

## Docker Inference Variables

These configure the containerized `faster-whisper` server (set in `.env` or `docker-compose.yml`):

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL` | `base.en` | Model size (base.en, small.en, medium.en, etc.) |
| `WHISPER_DEVICE` | `cpu` | Compute device (`cpu` or `cuda`) |
| `WHISPER_COMPUTE_TYPE` | `int8` | Quantization (`int8`, `float16`, `float32`) |
| `WHISPER_SOCKET_PATH` | `/run/whisper/whisper.sock` | Socket path inside container |
| `WHISPER_LANGUAGE` | `en` | Default transcription language |
| `WHISPER_VAD_THRESHOLD` | `0.5` | Voice activity detection threshold |
| `WHISPER_DOWNLOAD_ROOT` | `/models` | Model cache directory |

The host CLI connects to the socket mounted at `$XDG_RUNTIME_DIR/whisper/whisper.sock`.

## Core Paths

- `--whisper-cli` / `WHISPER_CLI` — Path to `whisper-cli` binary (native mode only)
- `--model` / `WHISPER_MODEL` — Path to GGML model file (native mode only)
- `--log-file` / `WHISPER_LOG_FILE` — Log file path

Defaults:

- whisper CLI: `whisper-cli` on `PATH`
- model: `~/.local/share/whisper-hotkey/models/ggml-base.en.bin`
- log: `/tmp/whisper_hotkey.log`

## Audio Selection

### Exact Override

Use this when you know the exact source name:

- `--source`
- `WHISPER_AUDIO_SOURCE`

### Priority List

Use this for stable fallback order:

- `--preferred-sources`
- `WHISPER_PREFERRED_SOURCES`

Format:

```text
source_one,source_two,source_three
```

If neither is set, the tool picks the first available capture source.

## Streaming Behavior

- `--chunk-seconds` / `WHISPER_CHUNK_SECONDS`
- `--overlap-seconds` / `WHISPER_OVERLAP_SECONDS`
- `--type-delay-ms` / `WHISPER_TYPE_DELAY_MS`
- `--language` / `WHISPER_LANGUAGE`

Recommended defaults:

- chunk: `1.8`
- overlap: `0.4`
- type delay: `1`
- language: `en`

## Service Environment File

For the systemd user service, place overrides in:

```text
~/.config/whisper-hotkey/whisper-hotkey.env
```

The service will load that file automatically if it exists.
