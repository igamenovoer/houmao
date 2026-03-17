## Why

The repository now has a mailbox system, but it does not yet provide one self-contained tutorial pack that demonstrates the operator-facing roundtrip workflow end to end. That gap makes it harder for developers to learn the intended `start-session` plus runtime `mail` flow, verify it from a clean checkout, and keep the example aligned with real behavior as the mailbox system evolves.

## What Changes

- Add a new self-contained tutorial pack under `scripts/demo/` that demonstrates two mailbox-enabled agents exchanging a roundtrip message through external runtime control.
- Package the tutorial as tracked inputs, a one-click `run_demo.sh`, a sanitized expected report, and a step-by-step README that exposes the underlying commands instead of treating the script as a black box.
- Drive the demo through the supported runtime surfaces: `build-brain --blueprint`, `start-session --blueprint`, `mail send`, `mail check`, `mail reply`, and `stop-session`.
- Make the v1 tutorial explicitly CAO-backed by using `cao_rest` with two concurrent TUI-oriented sessions, while keeping mailbox enablement visible through `start-session --mailbox-*` overrides.
- Define a default quick-start pair of tracked blueprints for one Claude Code agent and one Codex agent, with credential selection owned by the blueprint-bound brain recipes rather than by ad hoc runner flags.
- Persist and sanitize the demo's structured outputs so maintainers can compare current behavior with a tracked golden report and refresh that report intentionally with snapshot mode.
- Add focused validation coverage for the tutorial-pack workflow and, if needed, link the new pack from repo-owned docs or indexes that surface tutorial/demo entrypoints.

## Capabilities

### New Capabilities
- `mailbox-roundtrip-tutorial-pack`: Defines the repository-owned tutorial pack that teaches and verifies a two-agent mailbox roundtrip workflow under `scripts/demo/`.

### Modified Capabilities

## Impact

- Affected code: new tutorial-pack assets under `scripts/demo/`, pack-local sanitization/verification helpers, and any minimal runtime/docs touch points needed to keep the pack aligned with CAO-backed mailbox workflows.
- Affected systems: CAO-backed runtime session startup, runtime-owned mailbox operations, blueprint-driven brain selection, demo/tutorial-pack verification flow, and demo-facing operator documentation.
- Affected tests: focused report/helper coverage plus subprocess-style runner or integration coverage for the mailbox tutorial workflow and expected-report contract.
