## Why

The plain agent-definition fixture still carries stale launch and lifecycle guidance from the retired root-level `houmao-mgr agents ...` command shape, which makes it a poor seed for testing the new scoped CLI. The fixture also exposes a mismatch between documented direct brain-build examples, preset selector resolution, and empty-skill smoke presets.

## What Changes

- Refresh `tests/fixtures/plain-agent-def/` guidance and role prompts so they describe the current plain native-agent root layout, passive-server/managed-agent API wording, and scoped CLI lifecycle boundaries.
- Update maintained smoke/manual consumers that still invoke retired root-level commands to use `project agents launch` for birth and `agents single --agent-id ...` for selected-agent follow-up lifecycle.
- Clarify or repair direct native-agent brain build behavior for preset selectors and explicit empty skill lists so fixture smoke presets can be tested intentionally.
- Add coverage that prevents fixture docs, manual smoke helpers, and CLI examples from regressing to retired `agents launch|stop|cleanup` paths.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-fixture-contracts`: Clarify that the plain direct-dir fixture is seed/native-agent material, not a maintained public launch root, and that its guidance must avoid retired command paths and stale `agents/` path names.
- `claude-official-login-fixture-smoke-validation`: Update the official-login smoke flow to launch through maintained project-backed birth and clean up through scoped selected-agent lifecycle commands.
- `houmao-mgr-native-agent-internals-cli`: Clarify direct brain-build preset selector expectations and whether an explicit empty preset skill list is a valid internal build input.

## Impact

- Affected fixture/docs: `tests/fixtures/plain-agent-def/**`, especially `README.md`, `MIGRATION.md`, `roles/README.md`, `skills/README.md`, and `roles/server-api-smoke/system-prompt.md`.
- Affected smoke helper: `tests/manual/manual_claude_official_login_smoke.py`.
- Affected CLI/build behavior or tests: native-agent brain build preset resolution and empty-skill handling, plus CLI shape coverage for retired root `agents` commands.
- No new runtime dependency is expected.
