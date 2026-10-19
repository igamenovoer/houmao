# Spec Delta

## Purpose

Give managed CLI agents a provider-hook observation channel whose normalized lifecycle events merge with TUI parsing, so tracked state, prompt admission, and diagnostics rely on authoritative provider facts where terminal-text evidence is weak. The first adapter targets Claude Code; the observation model and degradation rules stay provider-neutral.

## ADDED Requirements

### Requirement: Managed Claude launches inject a session-scoped hook observer configuration

For managed Claude Code `local_interactive` launches with the channel enabled, the system SHALL install a session-scoped observer hook configuration through a launch-owned settings source without modifying operator-authored user or project settings. If the launch cannot safely add that source, the system SHALL continue the session without hook observation and report the channel as unavailable.

#### Scenario: Fresh managed launch installs the observer configuration

- **WHEN** a managed Claude `local_interactive` session launches with hook observation enabled
- **THEN** the launch arguments include a launch-owned settings source pointing at a generated session-scoped observer configuration
- **AND THEN** operator-authored user, project, and managed-home settings are not modified

#### Scenario: Conflicting settings source degrades the channel without failing the launch

- **WHEN** the resolved launch arguments already contain a settings source that the observer configuration cannot safely extend
- **THEN** the session launches without hook observation
- **AND THEN** the channel reports `unavailable` with a settings-conflict detail

### Requirement: Observer hooks never alter provider behavior

Observer hook handlers SHALL be strictly observational: they SHALL always exit successfully, emit nothing on standard output, return no decision or permission fields, and never block, deny, modify, or accelerate a provider action. A hook delivery or collector failure SHALL NOT fail the managed session.

#### Scenario: Collector outage does not disturb the provider

- **WHEN** the collector is unreachable while the provider attempts to deliver a hook event
- **THEN** the hook handler exits successfully without blocking or changing the provider action
- **AND THEN** the managed session continues normally

### Requirement: A per-session collector receives provider hook events

For each observed launch, the system SHALL run a per-session, loopback-only collector started before the provider. The collector SHALL authenticate deliveries with a per-session token, stamp each accepted event with receive order, acknowledge receipt within the provider hook timeout, and SHALL NOT resolve tracked state.

#### Scenario: Collector starts before the provider

- **WHEN** a hook-observed session launches
- **THEN** the collector is accepting events before the provider process starts
- **AND THEN** the provider's startup event can be captured

#### Scenario: Unauthenticated delivery is rejected

- **WHEN** an event arrives without the per-session token
- **THEN** the collector rejects it and does not append it to the event store

### Requirement: Raw hook events persist in a session-local restricted store

Raw hook events SHALL be appended to a session-local, permission-restricted, append-only store under the session root. The store SHALL be excluded from shared-registry records, remote APIs, and ordinary logs, and local tracking consumers SHALL be able to read it while the session is live.

#### Scenario: Event store is local and permission-restricted

- **WHEN** the collector accepts events for a live session
- **THEN** the raw event store exists under the session root with owner-only read and write permissions
- **AND THEN** no raw payload appears in shared-registry records or remote API payloads

### Requirement: Hook events normalize into a provider-neutral observation model

The system SHALL normalize each raw event into a provider-neutral observation carrying an event kind and, when present, session, prompt, tool, and subagent correlation identifiers. Unknown event names, unknown payload fields, and malformed payloads SHALL be tolerated, counted in diagnostics, and excluded from posture updates.

#### Scenario: Unknown and malformed events are tolerated

- **WHEN** the store contains an event with an unrecognized name and an event with a malformed payload
- **THEN** both are counted in channel diagnostics
- **AND THEN** neither changes the hook posture

### Requirement: Channel generations isolate provider launches

Each provider launch, resume, or relaunch SHALL start a new hook channel generation. Events from an older generation SHALL be ignored for current tracked state, and only the current generation SHALL participate in the tracked-state merge.

#### Scenario: Relaunch isolates old events

- **WHEN** a session is relaunched and events from the previous generation remain in the store
- **THEN** the new generation begins with a clean posture
- **AND THEN** old-generation events never arm or complete turns in the new generation

### Requirement: Hook posture derives provider lifecycle facts

The system SHALL reduce normalized events into a hook posture covering turn state, terminal result, blocked state, maintenance state, background-work pending, and active prompt correlation. A prompt-submitted event SHALL arm a turn even without gateway-submission evidence. Duplicate or orphaned events SHALL NOT create or complete turns.

#### Scenario: Direct provider input arms a turn

- **WHEN** a prompt is typed directly into the provider TUI and a prompt-submitted hook event arrives without any gateway submission record
- **THEN** the hook posture reports an active turn
- **AND THEN** tracked state reflects the active turn even though Houmao submitted nothing

#### Scenario: Orphan terminal event does not manufacture a completed turn

- **WHEN** a terminal hook event arrives with no active turn
- **THEN** it is recorded as an orphan diagnostic
- **AND THEN** no `last_turn` is emitted from it

### Requirement: Hook and TUI channels own separate fact domains

With an active channel, hook observations SHALL be the primary authority for turn start, turn end, terminal failure, permission waits, maintenance windows, and background work, while TUI tracking SHALL remain the sole authority for readiness, accepting input, draft input, pending input, modal rendering, stability, and interrupt outcomes. Disagreements SHALL be published as conflict diagnostics.

#### Scenario: Hook-active overrides a ready-looking surface for lifecycle state

- **WHEN** the hook posture reports an active turn and the TUI surface looks ready
- **THEN** tracked state reports the turn as active
- **AND THEN** a `hook_active_tui_ready` conflict diagnostic is published

#### Scenario: Hook-terminal preserves the TUI surface

- **WHEN** a hook terminal event settles the turn while the TUI still shows activity residue
- **THEN** `last_turn` settles from the hook event
- **AND THEN** TUI-owned surface fields continue to reflect the visible surface

### Requirement: Hook terminal events settle the tracked last turn

With an active channel, a hook turn-completion event SHALL settle `last_turn.result=success` without waiting for the TUI settle window, and a hook failure event SHALL settle `last_turn.result=known_failure` with the provider error class recorded. Hook events SHALL NOT settle `interrupted`, and TUI readiness and stability requirements are unchanged.

#### Scenario: Completion event settles success immediately

- **WHEN** a hook turn-completion event arrives for the active prompt while the TUI settle window is still open
- **THEN** the tracked state records `last_turn.result=success` immediately
- **AND THEN** prompt admission still waits for TUI readiness and stability

#### Scenario: Failure event records the provider error class

- **WHEN** a hook failure event arrives with a provider API error
- **THEN** the tracked state records `last_turn.result=known_failure`
- **AND THEN** diagnostics carry the provider error class

### Requirement: Permission requests mark the tracked turn blocked

With an active channel, a hook permission-request event SHALL mark the current turn blocked on operator action before the permission surface repaints, and a later resolution event SHALL clear the blocked mark while the turn continues. The blocked mark SHALL NOT by itself complete the turn.

#### Scenario: Permission request blocks before the modal paints

- **WHEN** a hook permission-request event arrives while the TUI has not yet rendered the permission dialog
- **THEN** the tracked state reports the turn blocked on operator action
- **AND THEN** the blocked fact is available to prompt admission immediately

### Requirement: Degraded hook channels preserve TUI-only behavior

When the hook channel is unavailable, stale, disabled by policy, untrusted, or errored, every existing tracked-state field, diagnostic availability, and admission outcome SHALL equal the TUI-only behavior, and a degraded channel SHALL NOT add refusal reasons or new required fields. Existing recorded TUI-only qualification replays SHALL produce unchanged results.

#### Scenario: Startup silence degrades to TUI-only

- **WHEN** no startup or later hook event arrives within the startup grace period
- **THEN** the channel reports `unavailable`
- **AND THEN** tracked state and admission behave exactly as they do for a session without the channel

#### Scenario: Mid-turn staleness returns authority to the TUI

- **WHEN** the channel was active but no event arrives within the staleness threshold while the TUI keeps changing
- **THEN** the channel reports `stale`
- **AND THEN** TUI evidence regains lifecycle authority until a current-generation event restores the channel

### Requirement: Hook channel health is inspectable

The system SHALL publish channel state, last event, event counters, and a short detail reason as additive optional fields on tracked-state, gateway, and local observation surfaces. Channel state SHALL distinguish active, unavailable, stale, disabled by policy, untrusted workspace, error, and stopped.

#### Scenario: Channel status is visible on local inspection surfaces

- **WHEN** an operator queries tracked state or gateway status for a hook-observed session
- **THEN** the response includes the additive channel status with state, counters, and last-event metadata
- **AND THEN** a consumer that ignores the new fields is unaffected

### Requirement: Public hook state is additive and secret-free

Public surfaces SHALL expose only event names, counters, failure classes, tool names, conflict reasons, and inspection-safe correlation identifiers. Raw payloads, prompt text, tool inputs and responses, assistant message text, secrets, and collector tokens SHALL NOT appear on any public, registry, or remote surface.

#### Scenario: Public payloads carry no raw hook content

- **WHEN** any tracked-state, gateway, registry, or passive-server payload is produced for a hook-observed session
- **THEN** it contains no raw hook payload, prompt text, tool input, assistant message text, or collector token

### Requirement: Session lifecycle manages hook artifacts

Session stop SHALL stop the collector, and session cleanup SHALL remove the session-owned hook subtree. Resume or relaunch SHALL install or repair the observer configuration before the provider starts. Hook cleanup SHALL NOT touch managed memory, provider homes, mailbox stores, or operator-owned paths.

#### Scenario: Stop and cleanup leave no residue

- **WHEN** a hook-observed session is stopped and cleaned up
- **THEN** the collector process is no longer running
- **AND THEN** the session-owned hook subtree is removed while memory, mailbox, and provider-home artifacts remain

### Requirement: Hook event selection is version-gated

The adapter SHALL configure only hook events supported at the provider's version, distinguishing required events from optional ones. If a required event or the settings-injection path is unsupported, the channel SHALL report unavailable and the session SHALL run TUI-only. Silence of an optional event SHALL NOT be treated as state evidence.

#### Scenario: Unsupported provider runs TUI-only

- **WHEN** the provider version lacks a required hook capability
- **THEN** the channel reports unavailable with a version detail
- **AND THEN** the session launches and tracks TUI-only
