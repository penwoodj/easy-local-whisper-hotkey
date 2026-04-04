# Contributing

## Development Flow

1. Create a topic branch from `main`.
2. Make the change with tests and docs.
3. Update `CHANGELOG.md` when behavior, packaging, or release-facing output changes.
4. Open a pull request.
5. Merge to `main` only after required checks are green.

## Pull Request Expectations

- Keep support scope honest. Do not claim Wayland or cross-platform support unless the code and docs both support it.
- Any change under `src/`, `packaging/`, or `scripts/` should come with a changelog update.
- If the merge is supposed to produce a stable GitHub release, update `src/whisper_hotkey/__init__.py`.
- Prefer additive compatibility over breaking current local workflows without migration notes.

## Local Checks

```bash
python3 -m pip install -e .[dev]
python3 -m unittest discover -s tests -p 'test_*.py' -v
ruff check .
ruff format --check .
mypy src
```

## Release Discipline

This repository uses a release workflow on merge to `main`.

- If `src/whisper_hotkey/__init__.py` contains a version that does not already have a Git tag, the merge-to-main workflow publishes that version.
- If the tag already exists, the workflow exits without creating a duplicate release.

That means contributors should treat version bumps deliberately, not casually.
