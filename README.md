# easy-local-whisper-hotkey

`easy-local-whisper-hotkey` is a local Linux desktop dictation tool for X11. It listens for `Ctrl+Space`, records from PipeWire or PulseAudio, transcribes with `whisper.cpp`, and types into the currently focused window.

This repository turns the original single-machine script into a releasable product skeleton:

- installable Python package with a stable CLI
- systemd user service for login startup
- Docker image for advanced/self-hosted usage
- documented install and troubleshooting flow
- GitHub Actions for review-oriented CI and merge-to-main releases

## Support Matrix

Current support for the packaged product is intentionally narrow:

- OS: Linux
- Desktop session: X11
- Audio stack: PipeWire or PulseAudio
- Typing backend: `xdotool`
- Transcription engine: external `whisper-cli` from `whisper.cpp`

Wayland, macOS, and Windows are not supported in this repository yet.

## Repository Layout

```text
src/whisper_hotkey/          Python package and CLI
tests/                       Unit and integration tests
packaging/systemd/           User service template
packaging/docker/            Container build
scripts/                     Release, install, and uninstall helpers
docs/                        Product, configuration, and release docs
.github/workflows/           Review CI and release automation
```

## CLI

The installed console entry point is `easy-local-whisper-hotkey`.

Common commands:

```bash
easy-local-whisper-hotkey run
easy-local-whisper-hotkey test --seconds 3
easy-local-whisper-hotkey list-sources
easy-local-whisper-hotkey print-config
easy-local-whisper-hotkey doctor
```

Backward-compatible direct flags still work:

```bash
easy-local-whisper-hotkey --test 3
```

## Native Install

The intended release install path is:

1. Install or build `whisper.cpp` and place `whisper-cli` on `PATH`, or point `WHISPER_CLI` to it.
2. Install a GGML model, or point `WHISPER_MODEL` to it.
3. Install the wheel with `pipx` or `pip --user`.
4. Install the systemd user service from `packaging/systemd/easy-local-whisper-hotkey.service`.
5. Run `easy-local-whisper-hotkey doctor` before enabling the service.

Detailed steps are in [docs/install.md](docs/install.md).

## Configuration

Runtime configuration can come from:

- CLI flags
- environment variables
- a systemd user `EnvironmentFile`

Important variables:

- `WHISPER_CLI`
- `WHISPER_MODEL`
- `WHISPER_AUDIO_SOURCE`
- `WHISPER_PREFERRED_SOURCES`
- `WHISPER_CHUNK_SECONDS`
- `WHISPER_OVERLAP_SECONDS`
- `WHISPER_TYPE_DELAY_MS`
- `WHISPER_LANGUAGE`
- `WHISPER_LOG_FILE`

See [docs/configuration.md](docs/configuration.md).

## Docker

Docker support is included, but it is secondary to native install. Full desktop typing from a container still requires host X11 and audio access. The image is primarily useful for:

- reproducible packaging
- advanced host setups
- CI build verification
- power users who understand X11/audio passthrough

The Dockerfile lives at [packaging/docker/Dockerfile](packaging/docker/Dockerfile).

## CI and Releases

This repository is set up for two automation paths:

- `CI`: runs on pull requests, merge queues, pushes to `main`, and manual dispatch
- `Release`: runs on merge to `main`, rebuilds the project, publishes artifacts, and creates a GitHub release when the package version does not already have a tag

The CI workflow is review-focused. It does not just say pass/fail; it runs repo hygiene checks, linting, typing, tests, packaging, Docker build verification, dependency review on pull requests, and a job summary that consolidates the results.

The release workflow assumes version discipline:

- if you merge code to `main` with a new `__version__` in `src/whisper_hotkey/__init__.py`, the workflow creates `v<version>`
- if that tag already exists, the workflow exits cleanly without creating a duplicate release

The release process is documented in [docs/release-process.md](docs/release-process.md).

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

This repository uses the MIT license. See [LICENSE](LICENSE).
