# Release Process

## Policy

This repository treats `main` as releasable.

- Pull requests are the only route into `main`.
- CI checks must pass before merge.
- Merge to `main` triggers the release workflow.

## Stable Release Rule

The version source of truth is `src/whisper_hotkey/__init__.py`.

- If tag `v<version>` does not exist, the workflow builds artifacts, publishes the container image, and creates a GitHub release.
- If the tag already exists, the workflow exits without creating a duplicate release.

That means a stable release requires a version bump in the merged change.

## Required PR Hygiene

For shipping changes:

1. update `CHANGELOG.md`
2. bump `src/whisper_hotkey/__init__.py` when the merge should create a stable release
3. keep docs aligned with support scope and install steps

## Release Assets

The release workflow publishes:

- wheel
- source distribution
- release bundle tarball
- SHA256 checksum file
- GHCR image tags for `v<version>` and `latest`

## Manual Recovery

If a release job fails after merge:

1. fix the build issue on a new pull request
2. merge to `main`
3. rerun the workflow manually if the version tag does not exist yet

If the tag already exists and the release assets are incomplete, delete the broken release and tag before rerunning.
