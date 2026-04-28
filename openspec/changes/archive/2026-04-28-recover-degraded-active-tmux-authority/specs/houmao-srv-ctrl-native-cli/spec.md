## MODIFIED Requirements

### Requirement: `houmao-mgr agents relaunch` exposes tmux-backed managed-session recovery
`houmao-mgr` SHALL expose `agents relaunch` as the native managed-session recovery command for tmux-backed managed agents.

`agents relaunch` SHALL support both explicit targeting by managed-agent identity and a current-session mode when the operator runs the command from inside the owning tmux session.

The command SHALL resolve the target session through manifest-first discovery, SHALL reuse the persisted session and built home, and SHALL NOT route through build-time `houmao-mgr agents launch`.

When the resolved local target is an active tmux-backed managed agent whose current tmux session still exists but whose contractual primary surface is missing, the command SHALL use the degraded-active recovery path for that same logical managed agent.

When the resolved local target is an active tmux-backed managed agent whose recorded tmux session no longer exists, the command SHALL use preserved relaunch authority to revive that same logical managed agent when supported runtime metadata remains available.

The command SHALL fail explicitly when the target is not tmux-backed, lacks valid manifest-owned relaunch authority, or cannot be resolved through supported selector or current-session discovery.

#### Scenario: Current-session relaunch uses tmux-local discovery
- **WHEN** an operator runs `houmao-mgr agents relaunch` from inside a tmux-backed managed session
- **THEN** `houmao-mgr` resolves that session through `HOUMAO_MANIFEST_PATH` or `HOUMAO_AGENT_ID`
- **AND THEN** it relaunches the managed agent surface without requiring an explicit selector

#### Scenario: Explicit relaunch recovers degraded active local authority
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id abc123`
- **AND WHEN** the resolved local managed agent still has an existing tmux session
- **AND WHEN** the contractual primary tmux surface is missing from that session
- **THEN** `houmao-mgr` routes the request through degraded-active recovery
- **AND THEN** it relaunches the existing logical managed session instead of requiring a fresh launch

#### Scenario: Explicit relaunch revives stale active local authority
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id abc123`
- **AND WHEN** the resolved local managed agent still claims lifecycle state `active`
- **AND WHEN** the recorded tmux session no longer exists
- **AND WHEN** supported relaunch metadata remains available
- **THEN** `houmao-mgr` routes the request through stale-active revival
- **AND THEN** it recreates live tmux-backed authority for that same logical managed agent

#### Scenario: Non-tmux-backed target fails clearly
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id abc123`
- **AND WHEN** the resolved managed agent is not a tmux-backed relaunchable session
- **THEN** the command fails explicitly
- **AND THEN** it does not pretend that build-time launch or a raw CAO path is a supported replacement

### Requirement: Native managed-agent local resume failures render as clean CLI errors
When a native `houmao-mgr agents ...` command resolves a local managed-agent target through shared-registry metadata and local controller resume or recovery fails with an expected realm-controller runtime-domain failure, `houmao-mgr` SHALL render that failure as explicit CLI error output rather than leaking a Python traceback.

This SHALL apply at minimum to local managed-agent commands that resume or recover a local target before dispatch, including:

- `houmao-mgr agents stop`
- `houmao-mgr agents prompt`
- `houmao-mgr agents interrupt`
- `houmao-mgr agents relaunch`

For `houmao-mgr agents stop` and `houmao-mgr agents relaunch`, the CLI SHALL attempt the supported degraded-active or stale-active recovery path before surfacing a contextual CLI error.

For commands that do not define a degraded recovery contract, stale or unusable local tmux-backed authority SHALL still surface as a clean non-traceback CLI error.

#### Scenario: Degraded active local stop succeeds without traceback
- **WHEN** an operator runs `houmao-mgr agents stop --agent-name alice`
- **AND WHEN** registry-first local discovery resolves managed agent `alice`
- **AND WHEN** local tmux inspection shows that the tmux session still exists but the contractual primary surface is missing
- **THEN** `houmao-mgr` uses degraded-active recovery instead of exiting on the first resume failure
- **AND THEN** the stop result is rendered without a Python traceback

#### Scenario: Local prompt target runtime failure still renders as CLI error text
- **WHEN** an operator runs `houmao-mgr agents prompt --agent-id agent-123 --prompt "hello"`
- **AND WHEN** registry-first local discovery resolves that managed agent
- **AND WHEN** local controller resume fails with an expected realm-controller runtime-domain error
- **THEN** `houmao-mgr` exits non-zero
- **AND THEN** stderr reports the failure as explicit CLI error text for that managed agent
- **AND THEN** stderr does not include a Python traceback
