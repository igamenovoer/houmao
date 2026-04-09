## ADDED Requirements

### Requirement: Native managed-agent local resume failures render as clean CLI errors

When a native `houmao-mgr agents ...` command resolves a local managed-agent target through shared-registry metadata and local controller resume fails with an expected realm-controller runtime-domain failure, `houmao-mgr` SHALL render that failure as explicit CLI error output rather than leaking a Python traceback.

This SHALL apply at minimum to local managed-agent commands that resume a local controller before dispatch, including:

- `houmao-mgr agents stop`
- `houmao-mgr agents prompt`
- `houmao-mgr agents interrupt`
- `houmao-mgr agents relaunch`

For stale tmux-backed local targets, the rendered failure SHALL preserve non-zero exit behavior and SHALL explain that the selected managed agent's local tmux-backed runtime authority is no longer live or otherwise unusable.

#### Scenario: Stale tmux-backed local stop target fails without traceback
- **WHEN** an operator runs `houmao-mgr agents stop --agent-name alice`
- **AND WHEN** registry-first local discovery resolves managed agent `alice`
- **AND WHEN** local controller resume fails because the persisted tmux session for that managed agent no longer exists
- **THEN** `houmao-mgr` exits non-zero
- **AND THEN** stderr reports a managed-agent contextual CLI error explaining that the local runtime authority is unusable
- **AND THEN** stderr does not include a Python traceback

#### Scenario: Local prompt target runtime failure still renders as CLI error text
- **WHEN** an operator runs `houmao-mgr agents prompt --agent-id agent-123 --prompt "hello"`
- **AND WHEN** registry-first local discovery resolves that managed agent
- **AND WHEN** local controller resume fails with an expected realm-controller runtime-domain error
- **THEN** `houmao-mgr` exits non-zero
- **AND THEN** stderr reports the failure as explicit CLI error text for that managed agent
- **AND THEN** stderr does not include a Python traceback
