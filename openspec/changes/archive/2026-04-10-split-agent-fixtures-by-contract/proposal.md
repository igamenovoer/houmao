## Why

`tests/fixtures/agents` currently mixes three different contracts: a plain filesystem-backed `--agent-def-dir` fixture root, a stand-in for the current `.houmao/agents` compatibility projection, and a host-local auth bundle stash. The maintained code and docs no longer treat those as the same thing, so the shared tree has drifted and now teaches the wrong structure to tests, demos, and maintainers.

## What Changes

- **BREAKING** Stop treating `tests/fixtures/agents` as the canonical all-purpose agent fixture root.
- Introduce separate supported fixture lanes for plain direct-dir agent-definition tests, host-local auth bundles, and project-overlay or demo-local generated agent trees.
- Define one maintained plain agent-definition fixture root that matches the current direct-dir contract, including `launch-profiles/` and human-named auth directories.
- Define one maintained local-only auth-bundle fixture root used by demos, smoke flows, and manual helpers that need host-local credentials without implying a full canonical agent-definition tree.
- Require maintained project-backed tests and demos to use fresh `.houmao/` overlays or demo-owned tracked `inputs/agents/` trees instead of depending on the broad repository fixture root.
- Update fixture guidance, maintained demos, and maintained manual flows so each one points at the correct fixture lane and stops claiming that one tree matches every current workflow.
- Leave archival legacy demos explicitly legacy rather than using them to define the current maintained fixture contract.

## Capabilities

### New Capabilities
- `agent-fixture-contracts`: define the supported repository fixture families, their directory shapes, their ownership rules, and which maintained workflows may depend on each family.

### Modified Capabilities
- `runtime-agent-dummy-project-fixtures`: realign narrow runtime, mailbox, and probe-skill fixtures with the split fixture-lane contract instead of the overloaded `tests/fixtures/agents` root.
- `shared-tui-tracking-demo-pack`: replace the maintained demo's dependency on `tests/fixtures/agents/tools/<tool>/auth/...` with the dedicated auth-bundle fixture lane while preserving demo-local generated `default` aliases.
- `minimal-agent-launch-demo`: replace the maintained demo's dependency on `tests/fixtures/agents/tools/<tool>/auth/...` with the dedicated auth-bundle fixture lane while preserving demo-local generated `default` aliases.
- `claude-official-login-fixture-smoke-validation`: relocate and clarify the supported `official-login` Claude smoke bundle and smoke flow away from the overloaded fixture root.

## Impact

- Affected code: test fixture helpers, maintained demo asset loaders, manual smoke scripts, and any helper that currently hardcodes `tests/fixtures/agents` for auth-bundle discovery.
- Affected repository structure: `tests/fixtures/` layout, fixture README guidance, and local-only encrypted auth-bundle handling.
- Affected docs: fixture guidance, maintained demo READMEs, and the Claude vendor-login smoke documentation.
- Affected tests: demo-pack unit tests, direct-dir credential tests, manual smoke scripts, and other maintained checks that currently assume `tests/fixtures/agents` is both canonical and current.
