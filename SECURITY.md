# Security Policy

## Reporting a Vulnerability

Do not open public issues for sensitive vulnerabilities.

Instead:

1. Send a private report to the maintainer.
2. Include reproduction steps, affected versions, and any known mitigations.
3. State whether the issue can lead to arbitrary key injection, credential capture, or unintended microphone access.

## Scope Notes

The product has elevated trust requirements because it:

- reads microphone input
- grabs a global hotkey in X11
- injects text into the focused window

Security review should focus on:

- unintended keystroke injection
- shell command safety
- environment and path handling
- service startup behavior
- release artifact integrity
