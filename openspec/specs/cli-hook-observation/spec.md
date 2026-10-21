# cli-hook-observation Specification

## Purpose

Give managed CLI agents a provider-hook observation channel whose normalized lifecycle events merge with TUI parsing, so tracked state, prompt admission, and diagnostics rely on authoritative provider facts where terminal-text evidence is weak. The first adapter targets Claude Code; the observation model and degradation rules stay provider-neutral.

## Requirements

### Requirement: Managed Claude launches inject a session-scoped hook observer configuration

For managed Claude `local_interactive` launches with the channel enabled, the system SHALL install the observer hook configuration by marker-merging a Houmao-owned block into the managed home's `settings.json`, preserving bundle and operator hook entries and leaving operator user/project settings untouched. An unmergeable home MAY fall back to a launch-owned `--settings` source; if neither path is safe, the session continues without hook observation and the channel reports `unavailable`.

#### Scenario: Fresh managed launch installs the observer configuration

- **WHEN** a managed Claude `local_interactive` session launches with hook observation enabled
- **THEN** the managed home's `settings.json` carries the Houmao-owned observer block alongside the preserved bundle and operator hook entries, rewritten for the current channel generation
- **AND THEN** no `--settings` argument is added and operator-authored user and project settings are not modified

#### Scenario: Unmergeable settings surface degrades the channel without failing the launch

- **WHEN** the managed home settings file cannot be safely merged and no fallback settings source can be safely added
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

### Requirement: Managed Kimi launches inject a validated hook observer configuration

For managed Kimi `local_interactive` launches with the channel enabled, the system SHALL merge a Houmao-owned observer block into the launch-owned runtime Kimi home's `config.toml` as `[[hooks]]` entries covering the full subscribed event set, with one entry per event, no matchers, and a bounded per-hook timeout. The merged file SHALL be validated by strict read-back (every hooks entry carries only the provider's allowed keys, a known event name, and a valid timeout) before the session is allowed to rely on the channel, because the provider silently voids the entire hooks section on any malformed entry. Installation SHALL require no operator action — the provider has no hook trust mechanism — and unsafe installation SHALL degrade the channel to `unavailable` without failing the launch. The observer block SHALL be idempotently rewritten per launch generation and removed on channel cleanup, leaving pre-existing `config.toml` content unmodified.

#### Scenario: Fresh managed Kimi launch installs validated hooks without operator action

- **WHEN** a managed Kimi `local_interactive` session launches with hook observation enabled
- **THEN** the runtime home's `config.toml` carries the observer `[[hooks]]` block alongside the launch-owned fields already present
- **AND THEN** the session's first prompt produces session-start, prompt-submit, turn-started, and stop hook events with no interactive prompt of any kind, with operator-managed Kimi files unmodified

#### Scenario: Malformed merged config is caught by the installer, not discovered dead

- **WHEN** the merged `config.toml` fails strict read-back validation (unknown key, unknown event, or out-of-range timeout in any hooks entry)
- **THEN** the session launches without hook observation
- **AND THEN** the channel reports `unavailable` with the validation failure detail

#### Scenario: Hook block lifecycle follows launch generations

- **WHEN** a managed Kimi session is relaunched or the hook observation channel is torn down
- **THEN** a relaunch rewrites the observer block for the new generation
- **AND THEN** teardown removes the observer block and leaves operator content in `config.toml` byte-identical

### Requirement: Kimi hook events normalize into the provider-neutral observation model

The system SHALL normalize each raw Kimi hook event into the provider-neutral observation model. Prompt-submit payloads carry the prompt as a structured content-part array and SHALL be collapsed to text. Tool events SHALL be paired by the payload's tool-call identifier; because Kimi tool events carry no turn identifier, turn correlation for tool events SHALL follow stream ordering within the armed turn. The Kimi turn identifier is an integer, session-scoped counter that continues across resume relaunches of the same session. A queued-input event SHALL be recorded as queue evidence without arming a new turn. Subagent start/stop events and nested turn-started events SHALL open and close nested scopes rather than new top-level turns, since subagent and parent turn identifiers are not distinct. Unknown or never-dispatched event families SHALL be tolerated and counted in diagnostics.

#### Scenario: Prompt payload collapses from content parts to text

- **WHEN** a Kimi prompt-submit event arrives with `prompt` as an array of content parts
- **THEN** the normalized record carries the joined text of the text parts
- **AND THEN** the raw structured shape is preserved in diagnostics

#### Scenario: Tool events pair by tool-call identifier within the armed turn

- **WHEN** pre-tool and post-tool events arrive carrying the same `tool_call_id` and no turn identifier
- **THEN** they are recorded as one paired tool call belonging to the currently armed turn
- **AND THEN** permission events carrying both `tool_call_id` and `turn_id` attribute to the same call

#### Scenario: Resume continues the session-scoped turn counter

- **WHEN** a session is relaunched with resume and emits a session-start event with a resume source
- **THEN** the new generation is recorded with the same provider session identifier
- **AND THEN** subsequent turn-started events continue the integer turn counter from the prior generation rather than restarting it

#### Scenario: Queued input does not open a new turn

- **WHEN** a prompt-queued event arrives while a turn is active
- **THEN** it is recorded as queue evidence with its prompt identifier and queue length
- **AND THEN** no new turn is armed and no second prompt-submit is expected for the steered input

### Requirement: Kimi hook terminal events settle tracked turns per Kimi semantics

For sessions observed through the Kimi adapter, a stop event SHALL latch turn success, and an interrupt event SHALL settle the interrupted outcome in place of a stop event. A provider stream ending without terminal events for an open turn, or a session-end event arriving with an open turn, SHALL leave the turn truthfully unknown and SHALL NOT record success. A clean headless run that ends without a session-end event after a latched stop SHALL be treated as terminal-settled with the missing session-end named as a diagnostic gap.

#### Scenario: Esc interrupt settles interrupted from hook evidence

- **WHEN** the operator interrupts an active Kimi turn and an interrupt event arrives with `reason=cancelled`
- **THEN** the tracked turn settles with the interrupted outcome from hook evidence
- **AND THEN** no stop event follows for the aborted turn and no success is latched

#### Scenario: Terminal gap never records success

- **WHEN** the provider process ends without stop, interrupt, or session-end events for an open turn
- **THEN** the tracked state reports the turn as unknown with a terminal-gap diagnostic
- **AND THEN** heartbeat cessation is recorded as liveness loss at heartbeat cadence granularity

### Requirement: Kimi permission and compaction events shape turn posture

For sessions observed through the Kimi adapter, a permission-request event SHALL mark the tracked turn blocked until the permission-result event settles it, for both approval and denial. After a denial, the provider emits a post-tool-failure event and the turn continues to a normal stop; denial SHALL NOT settle the turn as interrupted. Permission events fire only when the provider's permission policy resolves to asking the operator; sessions running under a never-ask policy produce no permission events, which SHALL be normal absence, not a channel fault. Compaction events SHALL delimit a maintenance window that preserves posture across the window, and the post-compaction turn SHALL start a new turn epoch; Kimi emits no compaction-sourced session-start event.

#### Scenario: Approval allow and deny both settle at the permission result

- **WHEN** a permission wait is approved and a permission-result event with `decision=approved` arrives
- **THEN** the blocked phase clears and the tool call proceeds to a post-tool event
- **WHEN** a permission wait is denied and a permission-result event with `decision=rejected` arrives
- **THEN** the blocked phase clears, the following post-tool-failure event is recorded as non-terminal evidence, and the turn continues

#### Scenario: Never-ask sessions have no permission events and stay unblocked

- **WHEN** a Kimi session runs under a never-ask permission policy for its whole lifetime
- **THEN** no permission-request or permission-result events arrive
- **AND THEN** the channel never asserts a blocked phase for that session

#### Scenario: Compaction holds posture across the maintenance window

- **WHEN** compaction begin and end events with a manual trigger arrive between two settled turns
- **THEN** tracked posture is preserved across the window without a false interruption
- **AND THEN** the next turn-started event is correlated as a new turn epoch with a fresh turn identifier, without any compaction-sourced session-start event

### Requirement: The Kimi adapter tolerates unexercised event families

The Kimi adapter subscribes the provider's full 20-event set and SHALL tolerate event families that a session never dispatches — including failure, background-task, notification, and cancellation-variant families that require conditions the session never produced — counting them in diagnostics as silent families rather than failing the channel. The adapter SHALL NOT rely on token-usage payloads or background-work mirrors for the tracked `work` axis, because Kimi stop events carry no background-task payload.

#### Scenario: Silent families degrade to diagnostics, not failure

- **WHEN** a subscribed event family never fires for an entire session
- **THEN** the channel records that family as silent in diagnostics
- **AND THEN** session tracking continues normally on the families that do fire
