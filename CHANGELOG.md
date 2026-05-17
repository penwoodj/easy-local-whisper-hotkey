# Changelog

All notable changes to this project should be documented in this file.

## [0.2.0] - 2026-05-17

### Security

- **CRITICAL**: Log file moved from world-readable `/tmp` to `XDG_RUNTIME_DIR` with `0o600` permissions. Speech transcripts are no longer readable by other users.
- **CRITICAL**: Lock file hardened with `O_EXCL|O_CREAT` and `0o600` permissions to prevent symlink attacks and race conditions.
- **HIGH**: Temp audio files registered with `atexit` for crash-safe cleanup.
- **HIGH**: Socket directory created with `chmod 700` in `setup.sh` and `Makefile`.
- **HIGH**: ANTHROPIC_API_KEY validated for `sk-ant-` prefix before use.
- **MEDIUM**: Inference server: 50MB request size limit to prevent memory exhaustion.
- **MEDIUM**: Inference server: JSON schema validation on socket messages.
- **MEDIUM**: Inference client: dynamic `os.getuid()` replaces hardcoded UID 1000 fallback.
- **MEDIUM**: Post-processor: pip installs use version constraints.
- **MEDIUM**: Socket path validated to be under `/run/` or `/tmp/`.
- **LOW**: Dockerfile builder: removed unnecessary `git` package.
- **LOW**: Release workflow: fixed `Dockerfile.inference` path reference.

### Features

- Single-command setup: `./scripts/setup.sh` or `make setup` bootstraps everything after clone.
- Makefile with common targets: setup, install, uninstall, build, test, doctor, clean, docker.
- Removed all hardcoded `/home/jon` paths from source and scripts.
- Fixed install scripts for Docker-first architecture.
- Rewrote README, docs/install.md, docs/configuration.md for Docker-first workflow.

### License

- Switched from MIT-only to dual MIT OR Apache-2.0.
- License files moved to `./licenses/`.
- Copyright assigned to Jon Penwood.

### Cleanup

- Removed abandoned tauri-app directory (21,000+ lines of dead code).
- Removed generated indicator frames, stale planning files, audit reports.
- Removed duplicate service file (`scripts/whisper-hotkey.service`).
- Fixed `pyproject.toml` description and keywords.

## [0.1.0] - 2026-04-03

- Packaged the original single-file dictation daemon as `whisper-hotkey`.
- Added an installable CLI, systemd service template, Dockerfile, docs, tests, and GitHub Actions workflows.
- Added CI checks for hygiene, linting, typing, tests, packaging, Docker build verification, dependency review, and review summaries.
- Added merge-to-main release automation that publishes GitHub release assets and a GHCR image.
