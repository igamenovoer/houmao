# Spec Delta

## MODIFIED Requirements

### Requirement: Direct human TUI interaction is a supported concurrent activity
The gateway SHALL treat direct human interaction with the managed TUI as a supported concurrent activity rather than as protocol corruption.

For parser-backed TUI control, when human interaction leaves the managed surface in a state that is not safely eligible for gateway injection, the gateway SHALL pause or defer queued terminal-mutating work until eligibility returns.

Direct human interaction SHALL NOT, by itself, invalidate already accepted queued work.

#### Scenario: Human interaction pauses queued injection without discarding queued work
- **WHEN** queued terminal-mutating work exists for a gateway-managed parser-backed TUI agent
- **AND WHEN** a human operator changes the managed TUI into a non-submit-ready surface before the queued work begins
- **THEN** the gateway defers injection until the surface is safely eligible again
- **AND THEN** the gateway retains the accepted queued work instead of discarding it solely because the human interacted with the TUI

#### Scenario: Human interaction during active work is recorded and reconciled
- **WHEN** a human operator changes a parser-backed managed TUI while a gateway-owned request is in progress
- **THEN** the gateway records that observation in its state or event history
- **AND THEN** the gateway reevaluates the active request outcome according to its recovery or retry policy instead of assuming the session is irreparably corrupted

#### Scenario: Human and Managed Input Share a Hermes Session

- **WHEN** a human uses the managed Hermes TUI while Houmao observes or submits work
- **THEN** the gateway records native activity and preserves the pinned conversation and any accepted managed admission
- **AND THEN** the human turn never settles a managed request

### Requirement: Gateway exposes semantic prompt submission separately from raw send-keys control

For gateway-managed tmux-backed sessions, the gateway SHALL keep semantic prompt submission separate from raw key/control-input delivery.

The gateway SHALL expose two semantic prompt surfaces:

- `POST /v1/requests` as the queued gateway request surface for `submit_prompt` and `interrupt`
- `POST /v1/control/prompt` as the direct prompt-admission surface for immediate handoff or an acknowledged queue outcome

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

For native headless targets, `POST /v1/control/prompt` SHALL additionally accept an optional structured `chat_session` selector object.

That headless-only selector SHALL use:

- `chat_session.mode = auto | new | current | tool_last_or_new | exact`
- `chat_session.id` required only when `mode = exact`

For headless prompt control:

- omitting `chat_session` SHALL be equivalent to `chat_session.mode = auto`
- `new` SHALL mean "use a fresh provider chat for this prompt"
- `current` SHALL mean "use the managed agent's pinned current provider session"
- `tool_last_or_new` SHALL mean "ask the underlying tool to resume its latest stored chat and start fresh if none exists"
- `exact` SHALL mean "use this exact provider session identifier"

The gateway SHALL additionally expose a dedicated raw control-input endpoint for send-keys style delivery. That endpoint SHALL accept exact `<[key-name]>` control-input sequences using the same contract as the runtime tmux-control-input capability, including optional full-string literal escaping.

Both semantic gateway prompt surfaces SHALL treat the provided prompt body as literal text, SHALL NOT interpret `<[key-name]>` substrings as special keys, and SHALL automatically submit once at the end.

The dedicated raw control-input endpoint SHALL NOT enqueue a durable `submit_prompt` request, SHALL NOT claim that a managed prompt turn was submitted, and SHALL NOT trigger gateway prompt-submission tracking hooks by itself.

For parser-backed TUI targets, `POST /v1/control/prompt` SHALL accept `chat_session.mode = new` and SHALL reject `chat_session.mode = auto | current | tool_last_or_new | exact` with validation semantics rather than ignoring the field.

Malformed `chat_session` payloads, including missing `id` for `exact` or unexpected `id` for other modes, SHALL be rejected with validation semantics.

#### Scenario: Gateway direct prompt control returns immediate dispatch semantics

- **WHEN** a caller uses `POST /v1/control/prompt` and the target accepts live handoff
- **THEN** the gateway reports `sent: true` and includes the operation identity and handoff outcome when available

#### Scenario: Direct prompt control acknowledges a queued operation

- **WHEN** direct prompt admission successfully reserves queued managed work or receives a native queued receipt
- **THEN** the gateway reports `outcome: queued`, `sent: false`, and the operation ID
- **AND THEN** it includes the native prompt ID when available

#### Scenario: Gateway queued prompt submission remains on the request surface

- **WHEN** a caller submits queued gateway work through `POST /v1/requests` with kind `submit_prompt`
- **THEN** the gateway treats that work as queued semantic prompt submission rather than generic key injection
- **AND THEN** the route remains distinct from `POST /v1/control/prompt`

#### Scenario: Gateway raw send-keys uses a separate control endpoint

- **WHEN** a caller needs to inject the raw control-input sequence `"/model<[Enter]><[Down]>"` into a live gateway-managed TUI
- **THEN** the caller uses the dedicated gateway raw control-input endpoint rather than `POST /v1/requests` or `POST /v1/control/prompt`
- **AND THEN** the gateway applies the exact `<[key-name]>` parsing rules without claiming that a semantic prompt turn was submitted

#### Scenario: Gateway send-prompt keeps special-key-looking text literal

- **WHEN** a caller submits gateway prompt text `type <[Enter]> literally`
- **THEN** the gateway semantic prompt path treats `<[Enter]>` as literal text
- **AND THEN** the gateway performs one automatic final submit instead of interpreting that substring as a raw keypress

#### Scenario: Headless direct prompt control accepts explicit tool-native latest selection
- **WHEN** a caller submits `POST /v1/control/prompt` for a native headless gateway target that supports `chat_session.mode = tool_last_or_new` and the caller selects it
- **THEN** the gateway resolves that request by asking the tool to resume its latest stored chat or start fresh if none exists
- **AND THEN** the gateway does not reinterpret that selector as the managed agent's current pinned session

#### Scenario: TUI direct prompt control accepts explicit new-session reset request
- **WHEN** a caller submits `POST /v1/control/prompt` for a parser-backed TUI gateway target with `chat_session.mode = new`
- **THEN** the gateway accepts that request as a TUI conversation-reset workflow
- **AND THEN** it does not reinterpret that selector as headless provider-session state

#### Scenario: TUI direct prompt control rejects unsupported explicit session selector
- **WHEN** a caller submits `POST /v1/control/prompt` for a parser-backed TUI gateway target with `chat_session.mode = current`
- **THEN** the gateway rejects that request with validation semantics
- **AND THEN** it does not ignore the selector and pretend that ordinary prompt control succeeded

#### Scenario: Hermes TUI Prompt Uses Its Pinned Conversation

- **WHEN** a direct semantic prompt targets a managed Hermes TUI
- **THEN** Houmao submits ordinary prompt text through its supported native control route
- **AND THEN** an explicit prompt-time session selector is refused before submission
- **AND THEN** changing the bound TUI conversation requires a verified managed session or lifecycle operation

#### Scenario: Hermes Headless Refuses Native Latest Selection

- **WHEN** a caller selects `chat_session.mode = tool_last_or_new` for a Hermes headless prompt
- **THEN** the gateway reports unsupported selection before starting the CLI
- **AND THEN** explicit new, current, and exact selections use the verified Hermes home and workspace

### Requirement: Gateway raw send-keys bypasses prompt-readiness and busy gating

For a target with qualified raw control input through `POST /v1/control/send-keys`, the gateway SHALL forward the exact control-input request without first requiring that the addressed agent is idle, stable, or prompt-ready.

The route SHALL reject unsupported input capabilities. It MAY still reject the request for ordinary gateway availability failures such as detached gateway state, reconciliation blocking, or invalid control-input payloads.

#### Scenario: Raw send-keys still forwards while the TUI is busy

- **WHEN** a caller submits `POST /v1/control/send-keys` for a target with qualified raw control input while the gateway-owned TUI state reports active work
- **THEN** the gateway forwards that raw control-input request immediately
- **AND THEN** it does not reject the request only because the agent is not prompt-ready

### Requirement: Gateway headless prompt surfaces accept request-scoped execution overrides
For native headless gateway targets with qualified request-scoped execution overrides, both semantic gateway prompt surfaces SHALL accept an optional request-scoped `execution.model` object:

- `POST /v1/control/prompt`
- `POST /v1/requests` with `kind = submit_prompt`

That `execution.model` object SHALL use the same normalized unified model-selection shape as Houmao launch-owned model configuration.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

For native headless targets with qualified request-scoped execution overrides, the gateway SHALL treat `execution` and `chat_session` as orthogonal controls:

- `chat_session` selects conversation continuity
- `execution.model` selects model and reasoning for the accepted prompt

When both fields are present, the gateway SHALL preserve both through prompt admission and headless execution.

The request-scoped execution override SHALL apply only to the accepted prompt being dispatched or dequeued.

The gateway SHALL NOT store execution state inside `chat_session.current`, `chat_session.startup_default`, or `chat_session.next_prompt_override`.

For TUI targets and Hermes headless targets, any supplied `execution` override on either semantic prompt surface SHALL be rejected with validation semantics rather than ignored.

#### Scenario: Headless direct prompt control accepts execution and chat-session together
- **WHEN** a caller submits `POST /v1/control/prompt` for a native headless gateway target with qualified execution overrides
- **AND WHEN** the request includes `chat_session.mode = current` and `execution.model.reasoning.level = 4`
- **THEN** the gateway preserves the explicit current-session selector for conversation continuity
- **AND THEN** the gateway applies reasoning level `4` only to that accepted prompt execution

#### Scenario: Headless queued prompt submission accepts the same execution override contract
- **WHEN** a caller submits `POST /v1/requests` with `kind = submit_prompt` for a native headless gateway target with qualified execution overrides
- **AND WHEN** the request payload includes `execution.model.name = "gpt-5.4-mini"`
- **THEN** the gateway accepts that queued semantic prompt request using the same execution-override contract as direct prompt control
- **AND THEN** the later dequeued headless prompt uses `gpt-5.4-mini` only for that queued request

#### Scenario: TUI direct prompt control rejects execution override
- **WHEN** a caller submits `POST /v1/control/prompt` for a TUI-backed gateway target
- **AND WHEN** the request includes `execution.model.name = "gpt-5.4-mini"`
- **THEN** the gateway rejects that request with validation semantics
- **AND THEN** it does not silently ignore the execution override and pretend that prompt control succeeded

#### Scenario: TUI queued prompt submission rejects execution override
- **WHEN** a caller submits `POST /v1/requests` with `kind = submit_prompt` for a TUI-backed gateway target
- **AND WHEN** the request payload includes `execution.model.reasoning.level = 2`
- **THEN** the gateway rejects that request with validation semantics
- **AND THEN** it does not silently queue a TUI prompt while dropping the requested execution override

### Requirement: Gateway attach applies configurable TUI tracking timings
The gateway companion SHALL accept optional gateway-owned TUI tracking timing configuration when attaching to a gateway-capable parser-backed TUI session.

The timing configuration SHALL include:

- watch poll interval seconds
- readiness stability threshold seconds
- completion stability seconds
- unknown-to-stalled timeout seconds
- stale-active recovery seconds
- final stable-active recovery seconds

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

When a timing value is omitted, the gateway attach flow SHALL preserve the existing default or previously persisted desired value for that field.

When a timing value is supplied, the gateway attach flow SHALL validate that it is greater than zero before starting the gateway companion.

The gateway companion SHALL apply the resolved timing values to its gateway-owned `SingleSessionTrackingRuntime` and underlying live TUI tracker.

The gateway attach flow SHALL persist the resolved timing configuration in gateway desired configuration so later attach or restart flows for the same gateway root reuse the selected values unless a stronger explicit override is supplied.

The gateway reset-context wait and poll constants SHALL remain unaffected by this timing configuration.

#### Scenario: Explicit attach timings configure gateway-owned TUI tracking
- **WHEN** an operator attaches a gateway to a parser-backed TUI session with explicit gateway TUI timing overrides
- **THEN** the gateway service starts its TUI tracking runtime with those resolved timing values
- **AND THEN** the gateway-owned TUI state lifecycle metadata reflects the configured completion stability, unknown-to-stalled, stale-active recovery, and final stable-active recovery values

#### Scenario: Later attach reuses persisted gateway TUI timings
- **WHEN** a gateway attach succeeds with explicit gateway TUI timing overrides
- **AND WHEN** the same gateway root is attached again without explicit timing overrides
- **THEN** the later attach reuses the persisted desired timing values for gateway-owned TUI tracking

#### Scenario: Invalid gateway TUI timing value is rejected before attach
- **WHEN** a gateway attach request supplies a gateway TUI timing value less than or equal to zero
- **THEN** the attach request fails before starting or reusing the gateway service process
- **AND THEN** the failure identifies the invalid timing field

#### Scenario: Gateway reset-context timing remains separate
- **WHEN** a gateway is attached with gateway TUI tracking timing overrides
- **THEN** those overrides affect continuous TUI tracking, stale-active recovery, and final stable-active recovery
- **AND THEN** they do not change the gateway reset-context wait or reset-context polling constants

#### Scenario: Hermes Gateway Has No Parser Timing Controls

- **WHEN** a gateway attach request supplies terminal tracking timings for a Hermes TUI
- **THEN** the gateway refuses the unsupported settings and creates no terminal tracker

### Requirement: Gateway direct prompt control uses explicit admission policies

Gateway direct prompt control through `POST /v1/control/prompt` SHALL accept `admission_policy = ready_only | if_no_pending | always` and SHALL default omitted policy to `ready_only`.

For a parser-backed TUI target, `ready_only` SHALL require the existing stable prompt-ready contract and `surface.pending_input=no`. It SHALL reject busy, pending, or pending-unknown observations.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

For a parser-backed TUI target, `if_no_pending` SHALL ignore prompt-readiness and busy posture, dispatch only when the latest gateway-owned tracked snapshot reports `surface.pending_input=no`, reject `yes` with `error_code=pending_input`, and reject `unknown` with `error_code=pending_input_unknown`.

For a parser-backed TUI target, `always` SHALL bypass tracked readiness and pending-input checks. Every policy SHALL still reject unavailable, detached, reconciliation-blocked, invalid-selector, incompatible-target, and unsupported-target requests.

When the addressed parser-backed TUI session has an active hook observation channel, `ready_only` SHALL additionally require that the merged hook posture reports neither an active nor a blocked turn, and `if_no_pending` SHALL additionally require that the hook posture does not report blocked. Hook-reported background work SHALL NOT by itself close any policy, and `always` SHALL remain unaffected by hook posture.

A hook channel that is unavailable, stale, disabled, untrusted, or errored SHALL NOT add refusal reasons: admission SHALL evaluate exactly the TUI-only facts above. Admission decision records SHALL include the hook channel state, the hook posture facts, and any conflict reasons used in the decision.

For parser-backed TUI targets, the admission decision SHALL be observational. The gateway SHALL NOT reserve the observed no-pending state or promise atomic compare-and-submit behavior across concurrent requests. Two calls that both observe `pending_input=no` MAY both dispatch before the provider TUI repaints.

Non-default admission policies SHALL be rejected for native headless targets, and native headless prompt control SHALL continue to reject overlapping active execution. For targets with reset-then-send support, interactive `chat_session.mode=new` SHALL require `ready_only` because reset-then-send depends on stable prompt readiness.

Prompt submission SHALL continue to arm explicit-input tracking where applicable, but the gateway SHALL NOT synthesize `surface.pending_input` from its dispatch, event, reminder, notifier, raw-input, or durable-request state.

For a Web interactive target, `ready_only` SHALL require native idle, unblocked, no-pending state; `if_no_pending` SHALL permit busy state only with an unblocked agent and empty native inbox; `always` SHALL bypass native readiness and pending-input checks. Each policy SHALL still verify the exact live host/agent incarnation and structural availability. Its native check and input insertion SHALL be atomic after asynchronous preparation. These policies authorize only the requested operation, not automatic prompt resend or cold-session activation.

#### Scenario: Default policy sends to a stable ready TUI with no pending input

- **WHEN** a caller omits `admission_policy`
- **AND WHEN** the addressed TUI satisfies the stable prompt-ready contract and reports `surface.pending_input=no`
- **THEN** the gateway dispatches the prompt under `ready_only`
- **AND THEN** the success response identifies `admission_policy=ready_only`

#### Scenario: Ready-only backs off while the TUI is busy

- **WHEN** a caller selects `ready_only` while the addressed TUI does not satisfy the stable prompt-ready contract
- **THEN** the gateway refuses the prompt with `error_code=not_ready`
- **AND THEN** it does not submit the prompt to the provider CLI

#### Scenario: Ready-only backs off when hooks report an active or blocked turn

- **WHEN** a caller selects `ready_only` for a session whose TUI satisfies the stable prompt-ready contract with `surface.pending_input=no`
- **AND WHEN** the active hook observation channel reports the turn active or blocked
- **THEN** the gateway refuses the prompt with `error_code=not_ready`
- **AND THEN** the refusal record carries the hook posture facts

#### Scenario: If-no-pending submits while busy when the queue is visibly empty

- **WHEN** a caller selects `if_no_pending` while the TUI is busy and the latest tracked snapshot reports `surface.pending_input=no`
- **THEN** the gateway dispatches the prompt to the provider CLI
- **AND THEN** it does not require `turn.phase=ready` or `surface.ready_posture=yes`

#### Scenario: If-no-pending backs off from an existing provider-native queue

- **WHEN** a caller selects `if_no_pending` and the latest tracked snapshot reports `surface.pending_input=yes`
- **THEN** the gateway refuses the prompt with `error_code=pending_input`
- **AND THEN** it does not add that prompt to the provider CLI queue

#### Scenario: If-no-pending backs off while hooks report blocked

- **WHEN** a caller selects `if_no_pending` and the latest tracked snapshot reports `surface.pending_input=no`
- **AND WHEN** the active hook observation channel reports the turn blocked on a permission request
- **THEN** the gateway refuses the prompt with `error_code=not_ready`
- **AND THEN** it does not dispatch the prompt

#### Scenario: Degraded hook channel adds no refusal reasons

- **WHEN** a caller selects `ready_only` or `if_no_pending` for a session whose hook channel is unavailable, stale, disabled, untrusted, or errored
- **AND WHEN** the TUI-only facts would admit the prompt
- **THEN** the gateway admits the prompt exactly as it would without the channel
- **AND THEN** the decision record carries the hook channel state without adding refusal reasons

#### Scenario: If-no-pending treats uncertainty conservatively

- **WHEN** a caller selects `if_no_pending` and the latest tracked snapshot reports `surface.pending_input=unknown`
- **THEN** the gateway refuses the prompt with `error_code=pending_input_unknown`
- **AND THEN** it does not reinterpret unknown as an empty provider queue

#### Scenario: Always submits despite visible pending input

- **WHEN** a caller selects `always` for an attached compatible TUI whose latest tracked snapshot reports `surface.pending_input=yes`
- **THEN** the gateway dispatches the prompt
- **AND THEN** structural availability and compatibility failures remain enforceable

#### Scenario: Closely spaced conditional submissions may both dispatch before repaint

- **WHEN** two `if_no_pending` calls for a parser-backed TUI target independently observe the same latest snapshot with `surface.pending_input=no`
- **THEN** both calls may dispatch before a later TUI capture reports the provider queue
- **AND THEN** the gateway does not claim an exactly-one reservation guarantee

#### Scenario: Later conditional submission reacts to observed pending state

- **WHEN** earlier submissions have reached the provider CLI and a later tracked snapshot reports `surface.pending_input=yes`
- **THEN** a later `if_no_pending` call backs off
- **AND THEN** a later `always` call may still dispatch

#### Scenario: Admission decision records carry hook facts

- **WHEN** the gateway accepts or refuses a prompt for a session with an active hook observation channel
- **THEN** the durable decision record includes the hook channel state, hook turn posture, hook terminal result, and any conflict reasons used

#### Scenario: Non-default policy is rejected for headless prompt control

- **WHEN** a caller selects `if_no_pending` or `always` for a native headless target
- **THEN** the gateway rejects the policy with validation semantics
- **AND THEN** it does not invent provider-native pending-input state or start overlapping headless work

#### Scenario: TUI new-session workflow requires ready-only policy

- **WHEN** a TUI direct prompt request combines `chat_session.mode=new` with `if_no_pending` or `always`
- **THEN** the gateway rejects the incompatible request with validation semantics
- **AND THEN** it does not begin a context-reset workflow from a busy or pending posture

#### Scenario: Web Ready-Only Rechecks After Human Input
- **WHEN** a Web request initially observes readiness but a human starts native work before its handoff
- **THEN** the native atomic admission rejects the ready-only request without queueing it

#### Scenario: Web If-No-Pending Explicitly Admits Busy Input
- **WHEN** an operator selects `if_no_pending` for a live unblocked Web agent whose native pending inbox is empty
- **THEN** a busy agent may accept that explicitly requested next-turn input
- **AND THEN** ordinary plugin delivery still uses ready-only admission

#### Scenario: Web Always Preserves Structural Refusals
- **WHEN** a Web `always` request carries a stale execution incarnation
- **THEN** it is refused without activating or targeting a replacement agent

#### Scenario: Hermes Observes an Idle Session Then Receives a Queued Receipt

- **GIVEN** a direct prompt targets a Hermes TUI using its supported `ready_only` policy
- **WHEN** Houmao verifies native idle and then receives a durable queued receipt for the exact prompt
- **THEN** the response reports `outcome=queued`, `sent=false`, the operation ID, and the native admission reference
- **AND THEN** the owner tracks that entry until its own settlement
- **AND THEN** the queued outcome confirms native acceptance while leaving turn start unconfirmed

#### Scenario: Hermes Cannot Pass Its Native Ready Check

- **WHEN** a direct prompt targets a Hermes TUI with known busy, blocked, stale, or unknown native readiness
- **THEN** the gateway returns the applicable readiness or availability error before native submit
- **AND THEN** a non-default admission policy is rejected as unsupported for this backend

### Requirement: Ordinary Plugin Event Refusals Are Immediate

The gateway SHALL attempt plugin-event dispatch only with ready gateway/plugin state, open core admission, idle available body, and applicable native readiness or tracked pending-input and active-hook guards. A failed readiness check SHALL return a retryable error without waiting, caching, queueing, or scheduling the message for later delivery.

#### Scenario: Busy Headless Agent Refuses an Event

- **WHEN** a plugin event arrives while a headless turn is active
- **THEN** the gateway returns HTTP 409 with a retryable readiness error
- **AND THEN** it starts no overlapping turn and stores no pending plugin message

#### Scenario: Ready TUI Still Has Provider Pending Input

- **WHEN** an event targets a parser-backed TUI whose tracked pending input is `yes` or `unknown`
- **THEN** the gateway returns a retryable readiness error even if the surface otherwise looks ready
- **AND THEN** it does not enqueue the event through the durable request queue

#### Scenario: Active Hook Posture Blocks a Visually Ready TUI

- **WHEN** a parser-backed TUI surface is stable and ready with no pending input but an active hook channel reports active or blocked work
- **THEN** the event request fails immediately instead of waiting for a different hook posture
- **AND THEN** stale, unavailable, or disabled hook channels add no gates beyond the established TUI-only rules

#### Scenario: Existing Accepted Work Conflicts With Immediate Dispatch

- **WHEN** existing gateway work prevents immediate plugin-event dispatch
- **THEN** the event request returns a retryable conflict and existing work retains its normal scheduling
- **AND THEN** the plugin request does not join that queue or hold the execution lock while waiting

#### Scenario: Readiness Changes Before Dispatch

- **WHEN** initial checks pass but the body becomes inadmissible by the final readiness check before dispatch
- **THEN** the original request returns an error and relinquishes its attempt
- **AND THEN** later readiness does not resume that request in the background

#### Scenario: Plugin Dispatch Does Not Add a Queued Request Kind

- **WHEN** a plugin event is dispatched through the immediate semantic path
- **THEN** no queued plugin-event request is created
- **AND THEN** the public request-kind set remains unchanged

#### Scenario: Hermes Accepts an Event After Native Idle Was Observed

- **WHEN** a Hermes TUI passes its final native readiness check and a human input races the plugin's native submit
- **THEN** a verified native queue receipt counts as confirmed handoff of the exact event
- **AND THEN** the gateway reports native queue acceptance separately from turn start and creates no Houmao retry spool

### Requirement: Body Loss During Plugin Dispatch Fails the Original Request

The gateway SHALL keep a plugin event in flight until confirming handoff to its captured body incarnation. Body loss, replacement, or unconfirmed handoff before response finalization SHALL fail the request unless the exact Hermes native handoff was already verified and recorded. A local queue acknowledgment or worker start SHALL NOT establish handoff. The gateway SHALL NOT retain a resend payload or continue the attempt against a replacement body.

#### Scenario: Body Dies After Gateway Admission but Before Handoff

- **WHEN** an event passes gateway admission and the addressed body dies before confirmed handoff
- **THEN** the original request returns HTTP 503 with a retryable body-unavailable error
- **AND THEN** its payload is discarded rather than cached for the next body

#### Scenario: Body Restarts Under the Same Logical Agent Name

- **WHEN** the body changes execution incarnation during dispatch while its logical agent/session identity remains the same
- **THEN** the original request fails with a retryable target-changed error
- **AND THEN** no surviving callback forwards its message to the replacement body

#### Scenario: Body Loss Is Observed After Handoff but Before Response

- **WHEN** handoff may have occurred but body death or replacement is observed before successful response finalization
- **THEN** the request returns a retryable error with uncertain dispatch outcome
- **AND THEN** the gateway does not claim a known unsent message or perform another attempt

#### Scenario: Headless Worker Starts Before Its Client Handoff

- **WHEN** a local headless worker thread starts but client dispatch has not yet been confirmed
- **THEN** the event request remains in flight within its finite deadline
- **AND THEN** a failed launch or missing confirmation returns an error instead of an early success

#### Scenario: Dispatch Confirmation Times Out

- **WHEN** a live request cannot confirm handoff within its finite deadline
- **THEN** it returns an explicit failure and revokes not-yet-dispatched request work
- **AND THEN** a later callback cannot resume delivery after body recovery

#### Scenario: Hermes Queued Receipt Cannot Be Verified

- **WHEN** the gateway loses the native response or body identity before verifying a Hermes queue receipt for the captured request
- **THEN** it returns the applicable refusal or uncertainty result
- **AND THEN** recovery cannot submit the event as a new native input

#### Scenario: Body Loss Follows Confirmed Hermes Native Handoff

- **WHEN** the gateway verifies and records the exact Hermes native receipt before the captured body is lost
- **THEN** the gateway preserves the recorded handoff and its queued or started disposition
- **AND THEN** body loss is tracked separately and does not authorize delivery to a replacement
