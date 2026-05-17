# easy-local-whisper-hotkey

`easy-local-whisper-hotkey` is a local Linux dictation tool for X11. It listens for `Ctrl+Space`, records from PipeWire or PulseAudio, transcribes with faster-whisper in a Docker container, and types into the currently focused window.

This repository provides an installable Python CLI with a Docker-based inference backend and systemd user service for login startup.

## Support Matrix

- OS: Linux
- Desktop session: X11
- Audio stack: PipeWire or PulseAudio
- Typing backend: `xdotool`

Wayland, macOS, and Windows are not supported.

## Architecture

The host CLI captures audio and sends it via Unix socket to a Docker container running faster-whisper (CTranslate2). The result is typed back into the focused window via xdotool. The container is fully sandboxed (no network, read-only, non-root user).

## Quick Start

Start the inference server:

```bash
docker compose up -d
```

Install the CLI:

```bash
pipx install easy-local-whisper-hotkey
```

Run dictation:

```bash
easy-local-whisper-hotkey run
```

Press `Ctrl+Space` to record. The CLI connects to the inference server via `$XDG_RUNTIME_DIR/whisper/whisper.sock`.

## Repository Layout

```
src/whisper_hotkey/          Python package (app.py, cli.py, inference_client.py, inference_server.py, indicator.py, postprocessor.py)
tests/                       Unit and integration tests
packaging/docker/            Dockerfile.inference + requirements.txt
packaging/systemd/           User service template
scripts/                     Release, install, uninstall helpers
docs/                        Configuration, install, troubleshooting, release docs
.github/workflows/           CI and release automation
docker-compose.yml           Docker Compose for inference server
```

## CLI

The entry point is `easy-local-whisper-hotkey`.

Common commands:

```bash
easy-local-whisper-hotkey run           # Start dictation daemon
easy-local-whisper-hotkey test --seconds 3    # Test recording and transcription
easy-local-whisper-hotkey list-sources   # List available audio sources
easy-local-whisper-hotkey print-config   # Print effective configuration
easy-local-whisper-hotkey doctor         # Diagnose setup issues
```

Backward-compatible direct flags still work:

```bash
easy-local-whisper-hotkey --test 3
```

## Docker Setup

The inference server runs in a Docker container built from `packaging/docker/Dockerfile.inference`. Use docker compose:

```bash
docker compose up -d
```

The container mounts `$XDG_RUNTIME_DIR/whisper:/run/whisper` for socket sharing. It is fully isolated (no network, drop all capabilities, non-root user). The base.en model is pre-downloaded during build.

## Native Install

For advanced users, you can skip Docker and use whisper-cli directly:

1. Install whisper-cli (whisper.cpp)
2. Install a GGML model
3. Point `WHISPER_CLI` and `WHISPER_MODEL` environment variables
4. Run `easy-local-whisper-hotkey run`

This bypasses the Docker container and runs transcription natively on the host.

## Configuration

Runtime configuration comes from:

- CLI flags
- Environment variables
- systemd user `EnvironmentFile` (at `~/.config/whisper-hotkey/whisper-hotkey.env`)

Important variables:

- `WHISPER_AUDIO_SOURCE`
- `WHISPER_PREFERRED_SOURCES`
- `WHISPER_CHUNK_SECONDS`
- `WHISPER_OVERLAP_SECONDS`
- `WHISPER_TYPE_DELAY_MS`
- `WHISPER_LANGUAGE`
- `WHISPER_LOG_FILE`
- `WHISPER_CLI` (native only)
- `WHISPER_MODEL` (native only)

See [docs/configuration.md](docs/configuration.md).

## CI and Releases

Two automation paths:

- `CI`: runs on pull requests, merge queues, pushes to `main`, and manual dispatch
- `Release`: runs on merge to `main`, rebuilds the project, publishes artifacts, and creates a GitHub release when the version tag does not exist

CI runs repo hygiene checks, linting, typing, tests, packaging, Docker build verification, and dependency review. The release workflow assumes version discipline in `src/whisper_hotkey/__init__.py`.

See [docs/release-process.md](docs/release-process.md).

## Local Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e .[dev]
python3 -m unittest discover -s tests -t . -p 'test_*.py' -v
ruff check .
ruff format --check .
mypy src
```

## License

MIT. See [LICENSE](LICENSE).