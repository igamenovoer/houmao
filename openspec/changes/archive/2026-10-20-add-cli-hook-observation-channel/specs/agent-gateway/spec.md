# Spec Delta

## MODIFIED Requirements

### Requirement: Gateway direct prompt control uses explicit admission policies

Gateway direct prompt control through `POST /v1/control/prompt` SHALL accept `admission_policy = ready_only | if_no_pending | always` and SHALL default omitted policy to `ready_only`.

For a TUI-backed target, `ready_only` SHALL require the existing stable prompt-ready contract and `surface.pending_input=no`. It SHALL reject busy, pending, or pending-unknown observations.

For a TUI-backed target, `if_no_pending` SHALL ignore prompt-readiness and busy posture, dispatch only when the latest gateway-owned tracked snapshot reports `surface.pending_input=no`, reject `yes` with `error_code=pending_input`, and reject `unknown` with `error_code=pending_input_unknown`.

For a TUI-backed target, `always` SHALL bypass tracked readiness and pending-input checks. Every policy SHALL still reject unavailable, detached, reconciliation-blocked, invalid-selector, incompatible-target, and unsupported-target requests.

When the addressed TUI session has an active hook observation channel, `ready_only` SHALL additionally require that the merged hook posture reports neither an active nor a blocked turn, and `if_no_pending` SHALL additionally require that the hook posture does not report blocked. Hook-reported background work SHALL NOT by itself close any policy, and `always` SHALL remain unaffected by hook posture.

A hook channel that is unavailable, stale, disabled, untrusted, or errored SHALL NOT add refusal reasons: admission SHALL evaluate exactly the TUI-only facts above. Admission decision records SHALL include the hook channel state, the hook posture facts, and any conflict reasons used in the decision.

The admission decision SHALL be observational. The gateway SHALL NOT reserve the observed no-pending state or promise atomic compare-and-submit behavior across concurrent requests. Two calls that both observe `pending_input=no` MAY both dispatch before the provider TUI repaints.

Non-default admission policies SHALL be rejected for native headless targets, and native headless prompt control SHALL continue to reject overlapping active execution. TUI `chat_session.mode=new` SHALL require `ready_only` because reset-then-send depends on stable prompt readiness.

Prompt submission SHALL continue to arm explicit-input tracking where applicable, but the gateway SHALL NOT synthesize `surface.pending_input` from its dispatch, event, reminder, notifier, raw-input, or durable-request state.

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

- **WHEN** two `if_no_pending` calls independently observe the same latest snapshot with `surface.pending_input=no`
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
