# cli-hook-observation Delta

## ADDED Requirements

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
