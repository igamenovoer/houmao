# Spec Delta

## ADDED Requirements

### Requirement: Scoped Agent Commands Expose Native Home Inspection

`agents single` and `agents self` SHALL expose `home` for one active managed agent. Single scope SHALL use its group-level selector; self scope SHALL use the current registered session without selectors. Plain output SHALL identify the native home path, and root `--print-json` SHALL expose the typed descriptor. Inspection SHALL NOT build, launch, or repair a home.

#### Scenario: Operator Reads a Selected Agent Home
- **WHEN** an operator runs `houmao-mgr agents single --agent-id agent-123 home`
- **THEN** the command reports the authoritative home of active agent `agent-123`
- **AND** the leaf accepts no second target selector

#### Scenario: Agent Reads Its Own Home
- **WHEN** an agent runs `houmao-mgr agents self home` inside its registered session
- **THEN** it receives that agent's native home without an explicit target override

#### Scenario: Structured Home Inspection Is Requested
- **WHEN** root `--print-json` is used with a scoped home command
- **THEN** output contains the selected agent, backend/tool, native home path, and known selector variable
- **AND** it excludes credentials, file contents, and ambient environment

#### Scenario: Selected Home Cannot Be Established
- **WHEN** the active runtime has no authoritative native-home mapping
- **THEN** the command exits nonzero without guessing or creating a home

### Requirement: Scoped Agent Commands Expose Read Only Common State

Scoped `refresh --check` SHALL inspect skills/MCP as common-plugin without initiating reload or forced discovery. It SHALL expose capabilities, inventory coverage, per-resource freshness, evidence, boundaries, and health. It SHALL report native automatic updates independently of Houmao receipts and SHALL provide no common native-special-plugin inventory or freshness API.

#### Scenario: Operator Checks a Selected Agent
- **WHEN** an operator runs `houmao-mgr agents single --agent-id agent-123 refresh --check`
- **THEN** the command performs read-only common observation for that active agent
- **AND** it does not initiate native invalidation, reload, worker startup, or a model turn

#### Scenario: Agent Checks During Its Own Active Turn
- **WHEN** an agent invokes `houmao-mgr agents self refresh --check` during active work
- **THEN** it receives the available observation or explicit evidence limitation without waiting for its turn to finish

#### Scenario: Automatic Update Is Observed
- **WHEN** the body already applied external skill/MCP edits without a Houmao refresh receipt
- **THEN** check mode reports the evidenced current state without requiring that receipt

#### Scenario: Observation Is Incomplete
- **WHEN** check mode cannot establish full common freshness
- **THEN** it preserves pending or unknown per-resource results and exits nonzero
- **AND** it does not quietly perform a refresh to improve the answer

### Requirement: Scoped Agent Commands Expose Native Refresh

Single/self `refresh` SHALL observe common state before selecting verified no-op, automatic discovery, or native reload. The native operation SHALL be permitted to refresh native-special-plugin and other native resources. Output SHALL preserve common observations and native outcomes without claiming common-only or atomic effects, applying launch profiles, or restarting the agent.

#### Scenario: Operator Refreshes a Selected Agent
- **WHEN** an operator runs `houmao-mgr agents single --agent-name worker-a refresh`
- **THEN** refresh targets the uniquely resolved active agent and reports its typed common/native results without relaunch fallback

#### Scenario: Native Updates Make Refresh Redundant
- **WHEN** common observation establishes complete current state before manual refresh
- **THEN** the command reports `method=noop` and `outcome=already_current`
- **AND** it initiates no native refresh or provider work

#### Scenario: Native Reload Also Updates Extensions
- **WHEN** the qualified native operation reloads skills/MCP and native-specific extensions together
- **THEN** the command accepts its broader effects and reports the verified common result
- **AND** it does not claim to verify every native extension

#### Scenario: Agent Requests Mutating Reload During Its Active Turn
- **WHEN** an agent's current work prevents native reload admission
- **THEN** self refresh returns busy immediately without interruption, deferred queueing, or waiting for that same turn

#### Scenario: Single Scope Has No Selector
- **WHEN** single refresh or check has no group-level selector
- **THEN** usage or target resolution fails without inferring the caller's session

#### Scenario: Self Scope Is Outside a Registered Session
- **WHEN** self refresh or check is invoked outside a registered managed session
- **THEN** it fails without selecting another agent or server default

### Requirement: Refresh CLI Preserves Freshness Outcome and Exit Semantics

Check SHALL exit 0 only for complete confirmed common freshness. Refresh SHALL exit 0 for already-current, confirmed common refresh, or fully qualified automatic coverage with explicit future boundaries. Other outcomes SHALL exit nonzero. Both output modes SHALL preserve freshness, health, native effects, and safe limitations without equating unknown evidence with current state.

#### Scenario: Automatic Discovery Is Deferred
- **WHEN** qualified discovery covers common resources on the next step, turn, or load
- **THEN** refresh exits 0 with that boundary
- **AND** it does not claim that future activation already occurred

#### Scenario: Common Resources Require Relaunch
- **WHEN** a common resource remains restart-required after other changes applied
- **THEN** refresh exits nonzero and preserves the applied effects and pending remainder
- **AND** guidance points to separate relaunch without changing its conversation-selection policy

#### Scenario: Only a Native Extension Remains Pending
- **WHEN** common freshness and native readiness are confirmed but unrelated native extension code remains pending
- **THEN** that pending diagnostic alone does not make the common command fail
- **AND** output makes no claim of full native extension freshness

#### Scenario: Native Outcome Is Uncertain
- **WHEN** native completion or readiness cannot be established
- **THEN** refresh exits nonzero with its uncertainty and safe effect evidence
- **AND** cached common metadata does not turn that result into success

#### Scenario: Structured Observation Is Requested
- **WHEN** root `--print-json` is used with refresh or check
- **THEN** typed output preserves current/pending/unknown common state, scope, boundaries, and separate native diagnostics
- **AND** it contains no raw private configuration or credential-derived fingerprints

### Requirement: Refresh CLI Has No Restart or Installation Authority

Scoped refresh SHALL reject force, restart, installation, source-directory, desired-revision, replacement-content, and arbitrary-command options. Global/external scope SHALL NOT gain these single-runtime home/refresh controls. Existing relaunch SHALL retain manifest-backed generation and conversation selection as a separate command.

#### Scenario: Caller Attempts Forced Restart
- **WHEN** a caller supplies `--restart` or `--force` with refresh or check
- **THEN** usage validation fails before native effects

#### Scenario: Caller Attempts Installation
- **WHEN** a caller supplies package/source/replacement-content options
- **THEN** the command rejects them and leaves external update ownership with the caller

#### Scenario: Scope Help Shows Distinct Actions
- **WHEN** an operator reads single/self help and refresh help
- **THEN** home, refresh/check, and relaunch remain distinct supported operations
- **AND** global/external help does not offer the new body home/refresh controls

#### Scenario: Explicit Relaunch Follows Existing Policy
- **WHEN** an operator separately invokes relaunch
- **THEN** its existing launch-material generation and chat-session rules apply
- **AND** the refresh feature neither replaces those rules nor promises exact continuation by default
