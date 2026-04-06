## Why

Houmao now supports Claude vendor login-state projection, but the local fixture tree and smoke-validation flow still do not prove that a real vendor `.credentials.json` plus a minimized `.claude.json` can launch a Claude agent from a fresh temporary workdir. That gap leaves the maintained Claude vendor-login lane under-validated and keeps the local fixture guidance aligned to older auth-bundle shapes.

## What Changes

- Add a local-only Claude auth fixture contract named `official-login` under `tests/fixtures/agents/tools/claude/auth/` that carries vendor `.credentials.json` unchanged plus a minimized but present `.claude.json`.
- Add a maintained smoke-validation workflow that launches a lightweight Claude preset from `tmp/<subdir>` while pointing `HOUMAO_AGENT_DEF_DIR` at `tests/fixtures/agents`.
- Clarify that projected vendor login-state works without `claude_state.template.json` when `.claude.json` is already present, even when that `.claude.json` is intentionally minimized.
- Update local fixture guidance so Claude auth examples and validation instructions stop implying the older non-dotfile fixture names or a required state-template dependency for this lane.

## Capabilities

### New Capabilities
- `claude-official-login-fixture-smoke-validation`: Define the local-only `official-login` Claude auth fixture shape and the supported smoke-validation flow for launching a Claude agent from a fresh temp workdir with that fixture.

### Modified Capabilities
- `claude-cli-noninteractive-startup`: Clarify that projected vendor `.credentials.json` plus a present but minimized `.claude.json` is a valid unattended Claude startup lane and does not require `claude_state.template.json`.

## Impact

- Affected code: Claude runtime bootstrap and any helper or validation code that provisions local fixture-backed Claude launches.
- Affected assets: `tests/fixtures/agents/tools/claude/auth/**`, `tests/fixtures/agents/README.md`, Claude fixture presets or validation helpers, and related smoke-test coverage.
- Affected behavior: Maintainers get one explicit local fixture name and one reproducible temp-workdir launch flow for validating the maintained Claude vendor-login path.
