# Spec Delta

## MODIFIED Requirements

### Requirement: Gateway status separates gateway health, upstream-agent state, recovery, admission, surface eligibility, and execution state
The gateway SHALL publish a structured status model that separates gateway health from managed-agent connectivity, recovery state, request-admission state, and native-surface readiness.

That published status model SHALL be protocol-versioned and SHALL be shared by both `state.json` and `GET /v1/status`.

At minimum, the published gateway status SHALL distinguish:

- protocol version
- stable session identity
- current managed-agent instance epoch
- gateway health state
- managed-agent connectivity state
- managed-agent recovery state
- request-admission state
- native-surface kind and eligibility state
- active execution state
- gateway execution mode
- gateway host
- gateway port
- queue depth

When the gateway is running in `tmux_auxiliary_window` mode, the published gateway status SHALL additionally expose the authoritative tmux execution handle for that live gateway surface, including the tmux window index and tmux window identifier. It MAY also expose the tmux pane identifier.

When the gateway cannot safely classify the managed native surface, it SHALL publish an explicit unknown-like state rather than inferring readiness.

`gateway health state` SHALL support representing that no gateway instance is currently attached to an otherwise gateway-capable session.

`request-admission state` SHALL support representing that the gateway remains alive while terminal-mutating work is paused or rejected because the managed agent is recovering, unavailable, or requires reconciliation after rebinding.

#### Scenario: Managed-agent crash changes upstream status without corrupting gateway health
- **WHEN** the gateway companion remains alive but the managed agent crashes unexpectedly
- **THEN** the published status keeps gateway health separate from the managed-agent connectivity and recovery states
- **AND THEN** the gateway does not claim that the whole control plane is dead solely because the upstream agent failed

#### Scenario: Replacement upstream instance increments the managed-agent epoch
- **WHEN** bounded recovery rebinds the logical session to a replacement managed-agent instance
- **THEN** the published status reflects a new managed-agent instance epoch for that same stable session identity
- **AND THEN** clients can distinguish "same session, new upstream instance" from "same session, same upstream instance"

#### Scenario: Manual modal interaction changes surface eligibility without corrupting gateway health
- **WHEN** a human operator opens or leaves the managed TUI in a non-submit-ready modal surface
- **THEN** the gateway updates the published native-surface eligibility state to reflect that non-ready surface
- **AND THEN** the gateway does not mark itself unhealthy solely because the operator changed the TUI surface

#### Scenario: Foreground gateway status exposes the tmux execution handle
- **WHEN** the gateway companion runs in `tmux_auxiliary_window` mode
- **THEN** the published status includes `execution_mode=tmux_auxiliary_window`
- **AND THEN** the published status exposes the authoritative tmux window index and tmux window identifier for that live gateway surface

#### Scenario: Uncertain surface classification stays explicit
- **WHEN** the gateway cannot safely determine whether the managed native surface is ready for injection
- **THEN** the gateway publishes an explicit non-ready or unknown-like surface state
- **AND THEN** it does not silently treat the surface as submit-ready

#### Scenario: Web Readiness Does Not Depend on a Terminal Parser
- **WHEN** the attached agent's native surface is Web
- **THEN** status exposes its Web identity, native readiness, pending-input, and execution facts
- **AND THEN** a healthy supervisory tmux pane cannot substitute for native Web readiness


### Requirement: Gateway direct prompt control uses explicit admission policies

Gateway direct prompt control through `POST /v1/control/prompt` SHALL accept `admission_policy = ready_only | if_no_pending | always` and SHALL default omitted policy to `ready_only`.

For a terminal TUI-backed target, `ready_only` SHALL require the existing stable prompt-ready contract and `surface.pending_input=no`. It SHALL reject busy, pending, or pending-unknown observations.

For a terminal TUI-backed target, `if_no_pending` SHALL ignore prompt-readiness and busy posture, dispatch only when the latest gateway-owned tracked snapshot reports `surface.pending_input=no`, reject `yes` with `error_code=pending_input`, and reject `unknown` with `error_code=pending_input_unknown`.

For a terminal TUI-backed target, `always` SHALL bypass tracked readiness and pending-input checks. Every policy SHALL still reject unavailable, detached, reconciliation-blocked, invalid-selector, incompatible-target, and unsupported-target requests.

When the addressed terminal TUI session has an active hook observation channel, `ready_only` SHALL additionally require that the merged hook posture reports neither an active nor a blocked turn, and `if_no_pending` SHALL additionally require that the hook posture does not report blocked. Hook-reported background work SHALL NOT by itself close any policy, and `always` SHALL remain unaffected by hook posture.

A hook channel that is unavailable, stale, disabled, untrusted, or errored SHALL NOT add refusal reasons: admission SHALL evaluate exactly the TUI-only facts above. Admission decision records SHALL include the hook channel state, the hook posture facts, and any conflict reasons used in the decision.

For terminal TUI targets, the admission decision SHALL be observational. The gateway SHALL NOT reserve the observed no-pending state or promise atomic compare-and-submit behavior across concurrent requests. Two calls that both observe `pending_input=no` MAY both dispatch before the provider TUI repaints.

Non-default admission policies SHALL be rejected for native headless targets, and native headless prompt control SHALL continue to reject overlapping active execution. Interactive `chat_session.mode=new` SHALL require `ready_only` because reset-then-send depends on stable prompt readiness.

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

- **WHEN** two `if_no_pending` calls for a terminal TUI target independently observe the same latest snapshot with `surface.pending_input=no`
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


## ADDED Requirements

### Requirement: DSH Web Ordinary Events Use Native Immediate Admission

Ordinary events targeting DSH Web SHALL use the captured live execution and native ready-only admission. Gateway/plugin health, core admission, native idle/readiness, pending-input state, and native interaction waits SHALL all be satisfied at handoff. Rejection or execution loss SHALL not create a delayed gateway or native delivery.

#### Scenario: Browser Input Wins the Admission Race
- **WHEN** a human starts work after gateway inspection but before an ordinary event's native insertion
- **THEN** the event receives an immediate retryable error and enters neither the native inbox nor the gateway queue

#### Scenario: Provider Replacement Follows Native Admission
- **WHEN** DSH replaces the bound host or agent while an admitted event still has a pending delivery or completion result
- **THEN** that result reports failure or uncertainty
- **AND THEN** the event is not rebound or replayed against the replacement

### Requirement: Web Gateway Observation Uses Structured Native State

A DSH Web gateway SHALL expose current native state and bounded recent state history through Web-specific control surfaces and common status/events. Observation SHALL follow both human and programmatic work without depending on terminal capture or browser DOM inspection. Terminal-only control routes SHALL return explicit unsupported semantics for a Web surface.

#### Scenario: Browser Approval Blocks Native Work
- **WHEN** the shared DSH session waits for a native human approval
- **THEN** gateway state reports the blocked interaction and ordinary prompt admission is closed
- **AND THEN** observing that state neither answers the approval nor marks the gateway itself unhealthy

#### Scenario: Terminal Tracking Is Requested for DSH Web
- **WHEN** a caller requests a terminal-parser state, terminal snapshot history, or raw keys for the Web agent
- **THEN** the gateway returns unsupported-capability information with the supported structured inspection surface
