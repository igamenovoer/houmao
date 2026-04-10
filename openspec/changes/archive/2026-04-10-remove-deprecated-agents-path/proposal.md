## Why

The repository already split fixture contracts into `plain-agent-def`, `auth-bundles`, and project- or demo-owned generated trees, but `tests/fixtures/agents/` still survives as a deprecated redirect path. Keeping that path around preserves ambiguity, leaves several live specs teaching the wrong source tree, and gives archived entrypoints one more hidden dependency on a contract the repository no longer wants to maintain.

## What Changes

- **BREAKING** Remove the deprecated `tests/fixtures/agents/` path from maintained repository surfaces instead of leaving it behind as a redirect stub.
- Update maintained specs, docs, helpers, and examples that still mention `tests/fixtures/agents/` so they point at `tests/fixtures/plain-agent-def/`, `tests/fixtures/auth-bundles/`, or demo-owned/generated trees as appropriate.
- Define the repository contract for fully removing the deprecated path so future maintained changes do not reintroduce it as a convenience alias.
- Update archived entrypoints that still default to `tests/fixtures/agents/` so they fail fast with clear guidance instead of assuming the removed path still exists.
- Remove maintained fixture guidance that presents the deprecated path as a migration surface for older local worktrees.

## Capabilities

### New Capabilities
- `deprecated-agents-fixture-removal`: define the repository behavior after the deprecated `tests/fixtures/agents/` path is removed entirely, including allowed replacement lanes and legacy-entrypoint handling.

### Modified Capabilities
- `claude-code-state-tracking-interactive-watch`: update the maintained interactive watch contract so it no longer describes `tests/fixtures/agents/` as the canonical fixture source.
- `claude-official-login-fixture-smoke-validation`: align the smoke fixture and launch flow with the fully removed deprecated path.
- `codex-openai-compatible-brain-profile`: update the documented Codex auth fixture example away from the removed path.
- `houmao-manage-credentials-skill`: stop teaching the deprecated fixture root as the example direct-dir target.
- `houmao-mgr-credentials-cli`: update direct-dir credential examples to use the maintained plain direct-dir lane instead of the removed path.
- `legacy-demo-entrypoint-guards`: make archived demo entrypoints fail clearly when they still depend on the removed deprecated fixture root.
- `minimal-agent-launch-demo`: keep the maintained demo contract aligned with dedicated auth bundles rather than the removed path.
- `runtime-agent-dummy-project-fixtures`: keep maintained runtime, mailbox, and probe-skill fixture requirements aligned with `tests/fixtures/plain-agent-def/`.
- `shared-tui-tracking-demo-pack`: keep the maintained demo contract aligned with demo-local generated trees plus dedicated auth bundles rather than the removed path.

## Impact

- Affected code: fixture path constants, archived demo defaults and preflight guards, maintained demo helpers, and manual smoke helpers.
- Affected repository structure: removal of the deprecated `tests/fixtures/agents/` directory and its redirect guidance.
- Affected docs and specs: current main specs and maintained guidance that still reference the deprecated path.
- Affected operators: local workflows that still reach for `tests/fixtures/agents/` will need to switch to the maintained replacement lane or accept explicit archived-demo failure messages.
