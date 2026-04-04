# GitHub Setup

## Repository Settings

Use these repository settings after pushing this repo to GitHub.

### Default Branch

- set the default branch to `main`

### Branch Protection or Ruleset for `main`

Require:

- pull request before merge
- at least 1 approval
- conversation resolution
- required status checks
- merge queue if you use it

Recommended required checks:

- `repo-hygiene`
- `lint`
- `unit-tests (3.11)`
- `unit-tests (3.12)`
- `package`
- `docker-build`
- `review-summary`

`dependency-review` should be required for pull requests if your org policy allows it, but it only runs on PR events.

### Merge Policy

Recommended:

- squash merge enabled
- merge commits disabled
- rebase merge optional

### Tag Policy

Protect `v*` tags so release tags are only created by maintainers or automation.

## Actions Permissions

Repository Actions permissions should allow:

- read access for normal CI
- `contents: write` and `packages: write` for the release workflow

The workflows already declare those permissions explicitly.

## Secrets

No custom secret is required for the provided release flow.

- release creation uses `GITHUB_TOKEN`
- GHCR publishing uses `GITHUB_TOKEN`

## Release Expectations

Merging to `main` only creates a release when:

1. the workflows pass
2. `src/whisper_hotkey/__init__.py` contains a new version
3. the corresponding `v<version>` tag does not already exist

## Suggested First Push Sequence

1. Create an empty GitHub repository.
2. Add it as `origin`.
3. Push `main`.
4. Open repository settings and configure the rules above.
5. Merge a pull request that bumps `__version__` to validate the first automated release.
