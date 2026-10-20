# cli-hook-observation Delta

## ADDED Requirements

### Requirement: Managed Codex launches inject a pre-trusted hook observer configuration

For managed Codex `local_interactive` launches with the channel enabled, the system SHALL write the observer `hooks.json` into the launch-owned runtime Codex home and SHALL pre-trust every handler through Houmao-owned `hooks.state` entries in that home's `config.toml` that reproduce the provider's trust keys and hashes. Installation SHALL require no operator action and no trust-bypass flag; unsafe installation SHALL degrade the channel to `unavailable` without failing the launch.

#### Scenario: Fresh managed Codex launch installs trusted hooks without operator action

- **WHEN** a managed Codex `local_interactive` session launches with hook observation enabled
- **THEN** the runtime home carries the observer `hooks.json` and a matching trust entry for every installed handler in its `config.toml`
- **AND THEN** the session reaches its first turn with hook events delivered and no trust-review prompt, with operator-managed Codex files unmodified

#### Scenario: Unsafe install degrades the channel without failing the launch

- **WHEN** the observer `hooks.json` or the pre-trust entries cannot be safely written for a launch
- **THEN** the session launches without hook observation
- **AND THEN** the channel reports `unavailable` with the install failure detail

### Requirement: Codex hook events normalize into the provider-neutral observation model

The system SHALL normalize each raw Codex hook event into the provider-neutral observation model, using the payload's turn identifier as the turn correlation key and the tool-use identifier to pair tool events. A repeated prompt-submission event carrying the running turn's identifier SHALL be treated as in-turn steered input, not a new turn. A permission-request event, which carries no tool-use identifier, SHALL be attributed within its turn to its tool call as the scenarios define.

#### Scenario: Lifecycle events map to provider-neutral evidence

- **WHEN** session-start events with startup, resume, or compact sources and compaction events with manual or auto triggers arrive
- **THEN** they are recorded as provider-neutral session and maintenance evidence
- **AND THEN** subagent identifiers, when present, are preserved as subagent correlation evidence

#### Scenario: Steered input does not open a new turn

- **WHEN** a prompt-submission event arrives carrying the same turn identifier as the currently active turn
- **THEN** it is recorded as in-turn input evidence for that turn
- **AND THEN** no new turn is armed

#### Scenario: Permission request attributes to its tool call without a tool-use identifier

- **WHEN** a permission-request event arrives in a turn where exactly one pre-tool event preceded it
- **THEN** the permission wait is attributed to that tool call
- **AND THEN** a later post-tool event carrying that call's tool-use identifier settles the wait

### Requirement: Codex hook terminal events settle tracked turns per Codex semantics

For sessions observed through the Codex adapter, a stop event SHALL latch turn success, and an interrupt event SHALL settle the interrupted outcome, including the approval-denied path where denial aborts the whole turn. A provider stream ending without terminal events for an open turn, or a session-end event arriving with an open turn, SHALL leave the turn truthfully unknown and SHALL NOT record success.

#### Scenario: Esc interrupt settles interrupted from hook evidence

- **WHEN** the operator interrupts an active Codex turn and an interrupt event arrives
- **THEN** the tracked turn settles with the interrupted outcome from hook evidence
- **AND THEN** no success is latched for that turn

#### Scenario: Terminal gap never records success

- **WHEN** the provider process ends without stop, interrupt, or session-end events for an open turn
- **THEN** the tracked state reports the turn as unknown with a terminal-gap diagnostic
- **AND THEN** no terminal success is recorded

### Requirement: Codex permission and compaction events shape turn posture

For sessions observed through the Codex adapter, a permission-request event SHALL mark the tracked turn blocked until the paired post-tool event (allow) or an interrupt event (deny, which aborts the turn) settles it. Compaction events SHALL delimit a maintenance window that preserves posture across the window, and the post-compaction turn SHALL start a new turn epoch.

#### Scenario: Approval denial aborts the turn

- **WHEN** a permission wait is denied at the provider's approval surface and an interrupt event follows without a post-tool event
- **THEN** the tracked turn settles with the interrupted outcome
- **AND THEN** the blocked phase is cleared

#### Scenario: Compaction holds posture across the maintenance window

- **WHEN** compaction begin and end events arrive between two settled turns
- **THEN** tracked posture is preserved across the window without a false interruption
- **AND THEN** the next turn's events are correlated as a new turn epoch

### Requirement: Codex hook event selection is version-gated at the supported floor

The Codex adapter SHALL define its subscribed event set per supported provider floor and SHALL tolerate events in the subscribed set that a given provider version never dispatches, counting them in diagnostics as unavailable families rather than failing the channel. At the current supported floor the adapter SHALL NOT rely on model-request events, subagent events, token-usage payloads, or background-work mirrors, because the provider does not dispatch or carry them.

#### Scenario: Undispatched events degrade to diagnostics, not failure

- **WHEN** a subscribed event family never fires for an entire session at the supported provider version
- **THEN** the channel records that family as unavailable in diagnostics
- **AND THEN** session tracking continues normally on the families that do fire
