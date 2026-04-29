## ADDED Requirements

### Requirement: `houmao-mgr agents stop` recovers verified broken active local lifecycle authority
When `houmao-mgr agents stop` resolves a local tmux-backed managed agent whose shared-registry record still claims `active` but local tmux authority is verified as stale or degraded, the command SHALL reconcile that broken active lifecycle state through a Houmao-native recovery path.

The command SHALL re-check the shared-registry generation and local tmux authority before mutating lifecycle state.

When preserved relaunch authority is readable, the command SHALL transition the same registry generation from `active` to `stopped`, clear active liveness and gateway metadata, preserve runtime relaunch locators, and report that the agent can be revived through `houmao-mgr agents relaunch`.

When preserved relaunch authority is unreadable, the command SHALL retire or remove the broken active record through the supported registry cleanup semantics and report that a fresh launch is required.

The command SHALL NOT publish the stopped transition with a new generation while the old generation still owns the active record.

#### Scenario: Stale active stop transitions the same generation to stopped
- **WHEN** an operator runs `houmao-mgr agents stop --agent-name alice`
- **AND WHEN** registry-first local discovery resolves a fresh active tmux-backed record for `alice`
- **AND WHEN** the recorded tmux session no longer exists
- **AND WHEN** the record still has readable manifest-owned relaunch authority
- **THEN** `houmao-mgr` transitions that same registry generation to lifecycle state `stopped`
- **AND THEN** the command succeeds without a shared-registry ownership conflict
- **AND THEN** the result includes the manifest path and session root for the recovered stopped session

#### Scenario: Degraded active stop tears down broken local authority before stopped transition
- **WHEN** an operator runs `houmao-mgr agents stop --agent-id abc123`
- **AND WHEN** the resolved active tmux-backed record's tmux session exists
- **AND WHEN** the contractual primary tmux surface is missing
- **AND WHEN** the record still has readable manifest-owned relaunch authority
- **THEN** `houmao-mgr` tears down the broken Houmao-owned tmux session
- **AND THEN** it transitions that same registry generation to lifecycle state `stopped`
- **AND THEN** the command succeeds without requiring the operator to kill tmux manually

#### Scenario: Broken active stop retires unrelaunchable local authority
- **WHEN** an operator runs `houmao-mgr agents stop --agent-name alice`
- **AND WHEN** the resolved active local tmux-backed record is stale or degraded
- **AND WHEN** the manifest or agent-definition authority needed for relaunch is unreadable
- **THEN** `houmao-mgr` retires or removes the broken active record through supported registry cleanup semantics
- **AND THEN** the command reports that the managed-agent identity cannot be relaunched from preserved local authority

### Requirement: `houmao-mgr agents stop` provides actionable recovery guidance on unexpected failures
When `houmao-mgr agents stop` cannot complete normally, the command SHALL include operator guidance that explains the safest supported next action.

The guidance SHALL include known target context when available, including `agent_name`, `agent_id`, `manifest_path`, `session_root`, and recorded tmux session name.

The guidance SHALL distinguish the operation phase that failed, including at least local tmux teardown, manifest/controller reconstruction, shared-registry lifecycle transition, and cleanup/reaping.

When Houmao can construct a precise follow-up command, the guidance SHALL include that exact command. Destructive recovery guidance SHALL prefer a dry-run command first unless the operator already requested destructive recovery.

The command SHALL NOT leave the operator needing to inspect `.houmao/runtime`, shared registry internals, or raw tmux state without a supported Houmao-native next step.

#### Scenario: Registry transition failure includes cleanup dry-run guidance
- **WHEN** an operator runs `houmao-mgr agents stop --agent-name alice`
- **AND WHEN** local tmux teardown or stale-authority classification completes
- **AND WHEN** publishing the stopped shared-registry transition fails unexpectedly
- **THEN** the stop error explains that runtime authority may already be stopped while the registry may remain stale
- **AND THEN** the error includes an exact `houmao-mgr agents cleanup session ... --purge-registry --dry-run` command using `--manifest-path`, `--session-root`, `--agent-id`, or `--agent-name` according to the most precise available selector

#### Scenario: Unknown stop failure preserves artifact context
- **WHEN** an operator runs `houmao-mgr agents stop --agent-id abc123`
- **AND WHEN** an unexpected runtime-domain failure prevents completion
- **THEN** `houmao-mgr` exits non-zero without a Python traceback
- **AND THEN** the error reports what target context was known
- **AND THEN** the error includes at least one supported Houmao-native inspection, retry, cleanup, or recovery command

#### Scenario: Stop guidance does not suggest unsafe prefix-only tmux reaping
- **WHEN** `houmao-mgr agents stop` detects possible leftover tmux sessions for a managed-agent name
- **THEN** any destructive reaping guidance requires Houmao-owned authority such as matching `HOUMAO_AGENT_ID` or `HOUMAO_MANIFEST_PATH`
- **AND THEN** the guidance does not tell the operator to kill every tmux session matching only a friendly-name or `HOUMAO-` prefix

## MODIFIED Requirements

### Requirement: `houmao-mgr agents relaunch` exposes tmux-backed managed-session recovery
`houmao-mgr` SHALL expose `agents relaunch` as the native managed-session recovery command for tmux-backed managed agents.

`agents relaunch` SHALL support both explicit targeting by managed-agent identity and a current-session mode when the operator runs the command from inside the owning tmux session.

The command SHALL resolve the target session through manifest-first discovery, SHALL reuse the persisted session and built home, and SHALL NOT route through build-time `houmao-mgr agents launch`.

When the resolved local target is an active tmux-backed managed agent whose current tmux session still exists but whose contractual primary surface is missing, the command SHALL use the degraded-active recovery path for that same logical managed agent.

When the resolved local target is an active tmux-backed managed agent whose recorded tmux session no longer exists, the command SHALL use preserved relaunch authority to revive that same logical managed agent when supported runtime metadata remains available.

For stale-active and degraded-active recovery, the command SHALL first transition the verified broken active record out of `active` using the expected existing generation before publishing a new live relaunch generation.

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
- **AND THEN** it does not fail with a shared-registry ownership conflict from the previous active generation

#### Scenario: Explicit relaunch revives stale active local authority
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id abc123`
- **AND WHEN** the resolved local managed agent still claims lifecycle state `active`
- **AND WHEN** the recorded tmux session no longer exists
- **AND WHEN** supported relaunch metadata remains available
- **THEN** `houmao-mgr` routes the request through stale-active revival
- **AND THEN** it recreates live tmux-backed authority for that same logical managed agent
- **AND THEN** it does not fail with a shared-registry ownership conflict from the previous active generation

#### Scenario: Stale-active revival failure leaves stopped continuity
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id abc123`
- **AND WHEN** stale-active recovery transitions the verified broken active record to stopped
- **AND WHEN** stopped-session revival then fails before publishing a new active generation
- **THEN** the registry record remains stopped and relaunchable when preserved authority is still valid
- **AND THEN** the operator is not left with a stale active record blocking retry

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

For `houmao-mgr agents stop`, contextual CLI errors SHALL include actionable recovery guidance with known target context and exact supported follow-up commands when available.

For commands that do not define a degraded recovery contract, stale or unusable local tmux-backed authority SHALL still surface as a clean non-traceback CLI error.

#### Scenario: Degraded active local stop succeeds without traceback
- **WHEN** an operator runs `houmao-mgr agents stop --agent-name alice`
- **AND WHEN** registry-first local discovery resolves managed agent `alice`
- **AND WHEN** local tmux inspection shows that the tmux session still exists but the contractual primary surface is missing
- **THEN** `houmao-mgr` uses degraded-active recovery instead of exiting on the first resume failure
- **AND THEN** the stop result is rendered without a Python traceback

#### Scenario: Stale active local stop succeeds without traceback
- **WHEN** an operator runs `houmao-mgr agents stop --agent-name alice`
- **AND WHEN** registry-first local discovery resolves managed agent `alice`
- **AND WHEN** local tmux inspection shows that the recorded tmux session no longer exists
- **THEN** `houmao-mgr` uses stale-active recovery instead of exiting on the first resume failure
- **AND THEN** the stop result is rendered without a Python traceback

#### Scenario: Local stop recovery failure includes guidance instead of traceback
- **WHEN** an operator runs `houmao-mgr agents stop --agent-id agent-123`
- **AND WHEN** registry-first local discovery resolves that managed agent
- **AND WHEN** local stop recovery fails with an expected realm-controller runtime-domain error
- **THEN** `houmao-mgr` exits non-zero
- **AND THEN** stderr reports the failure as explicit CLI error text for that managed agent
- **AND THEN** stderr includes a supported follow-up command for inspection, cleanup, retry, or recovery when one can be derived
- **AND THEN** stderr does not include a Python traceback

#### Scenario: Local prompt target runtime failure still renders as CLI error text
- **WHEN** an operator runs `houmao-mgr agents prompt --agent-id agent-123 --prompt "hello"`
- **AND WHEN** registry-first local discovery resolves that managed agent
- **AND WHEN** local controller resume fails with an expected realm-controller runtime-domain error
- **THEN** `houmao-mgr` exits non-zero
- **AND THEN** stderr reports the failure as explicit CLI error text for that managed agent
- **AND THEN** stderr does not include a Python traceback
