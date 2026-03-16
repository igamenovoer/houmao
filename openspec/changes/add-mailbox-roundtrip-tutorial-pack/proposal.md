## Why

The repository now has a mailbox system, but it does not yet provide one self-contained tutorial pack that demonstrates the operator-facing roundtrip workflow end to end. That gap makes it harder for developers to learn the intended `start-session` plus runtime `mail` flow, verify it from a clean checkout, and keep the example aligned with real behavior as the mailbox system evolves.

## What Changes

- Add a new self-contained tutorial pack under `scripts/demo/` that demonstrates two mailbox-enabled agents exchanging a roundtrip message through external runtime control.
- Package the tutorial as tracked inputs, a one-click `run_demo.sh`, a sanitized expected report, and a step-by-step README that exposes the underlying commands instead of treating the script as a black box.
- Drive the demo through the supported runtime surfaces: `build-brain`, `start-session`, `mail send`, `mail check`, `mail reply`, and `stop-session`.
- Persist and sanitize the demo's structured outputs so maintainers can compare current behavior with a tracked golden report and refresh that report intentionally with snapshot mode.
- Add focused validation coverage for the tutorial-pack workflow and, if needed, link the new pack from repo-owned docs or indexes that surface tutorial/demo entrypoints.

## Capabilities

### New Capabilities
- `mailbox-roundtrip-tutorial-pack`: Defines the repository-owned tutorial pack that teaches and verifies a two-agent mailbox roundtrip workflow under `scripts/demo/`.

### Modified Capabilities

## Impact

- Affected code: new tutorial-pack assets under `scripts/demo/`, likely a new helper module under `src/houmao/demo/`, and verification tooling for sanitizing and checking the demo report.
- Affected systems: mailbox-enabled runtime session startup, runtime-owned mailbox operations, demo/tutorial-pack verification flow, and demo-facing operator documentation.
- Affected tests: focused demo/tutorial integration coverage plus any helper-unit coverage for report sanitization or state handling.
