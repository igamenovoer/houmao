## ADDED Requirements

### Requirement: Gateway direct prompt control uses explicit admission policies

Gateway direct prompt control through `POST /v1/control/prompt` SHALL accept `admission_policy = ready_only | if_no_pending | always` and SHALL default omitted policy to `ready_only`.

For a TUI-backed target, `ready_only` SHALL require the existing stable prompt-ready contract and `surface.pending_input=no`. It SHALL reject busy, pending, or pending-unknown observations.

For a TUI-backed target, `if_no_pending` SHALL ignore prompt-readiness and busy posture, dispatch only when the latest gateway-owned tracked snapshot reports `surface.pending_input=no`, reject `yes` with `error_code=pending_input`, and reject `unknown` with `error_code=pending_input_unknown`.

For a TUI-backed target, `always` SHALL bypass tracked readiness and pending-input checks. Every policy SHALL still reject unavailable, detached, reconciliation-blocked, invalid-selector, incompatible-target, and unsupported-target requests.

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

#### Scenario: If-no-pending submits while busy when the queue is visibly empty

- **WHEN** a caller selects `if_no_pending` while the TUI is busy and the latest tracked snapshot reports `surface.pending_input=no`
- **THEN** the gateway dispatches the prompt to the provider CLI
- **AND THEN** it does not require `turn.phase=ready` or `surface.ready_posture=yes`

#### Scenario: If-no-pending backs off from an existing provider-native queue

- **WHEN** a caller selects `if_no_pending` and the latest tracked snapshot reports `surface.pending_input=yes`
- **THEN** the gateway refuses the prompt with `error_code=pending_input`
- **AND THEN** it does not add that prompt to the provider CLI queue

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

#### Scenario: Non-default policy is rejected for headless prompt control

- **WHEN** a caller selects `if_no_pending` or `always` for a native headless target
- **THEN** the gateway rejects the policy with validation semantics
- **AND THEN** it does not invent provider-native pending-input state or start overlapping headless work

#### Scenario: TUI new-session workflow requires ready-only policy

- **WHEN** a TUI direct prompt request combines `chat_session.mode=new` with `if_no_pending` or `always`
- **THEN** the gateway rejects the incompatible request with validation semantics
- **AND THEN** it does not begin a context-reset workflow from a busy or pending posture

### Requirement: Gateway prompt-control schema and CLI remove binary force behavior

The direct prompt-control request schema SHALL advance to schema version 2, SHALL contain `admission_policy`, and SHALL NOT contain `force`. Success and structured-refusal payloads SHALL report `admission_policy` and SHALL NOT report a boolean `forced` field.

The maintained `houmao-mgr agents single|self ... gateway prompt` commands SHALL expose `--admission-policy ready-only|if-no-pending|always` with `ready-only` as the default and SHALL NOT expose `--force` as an alias or deprecated compatibility flag.

Gateway event and diagnostic records for direct prompt decisions SHALL identify the selected admission policy and the observed readiness/pending facts used by conditional decisions.

#### Scenario: Version-two API accepts an explicit policy

- **WHEN** a caller sends a schema-version-2 direct prompt request with `admission_policy=if_no_pending`
- **THEN** the gateway validates and evaluates that named policy
- **AND THEN** the result or refusal reports the same policy

#### Scenario: Legacy force payload is rejected

- **WHEN** a caller sends a direct prompt-control payload containing `force` or schema version 1
- **THEN** strict request validation rejects the payload
- **AND THEN** the gateway does not translate it into an admission policy

#### Scenario: CLI maps hyphenated policy values to the API enum

- **WHEN** an operator runs `houmao-mgr agents single --agent-name worker gateway prompt --admission-policy if-no-pending --prompt ping`
- **THEN** the CLI sends `admission_policy=if_no_pending` through the selected managed-agent path
- **AND THEN** command output reports the selected policy instead of a forced boolean

#### Scenario: Removed force flag has no shim

- **WHEN** an operator invokes gateway prompt with `--force`
- **THEN** Click rejects the unknown option
- **AND THEN** help output directs current callers only through `--admission-policy`

## REMOVED Requirements

### Requirement: Gateway direct prompt control only dispatches when the addressed agent is prompt-ready unless forced

**Reason**: The binary `force` contract cannot express “submit while busy only if no provider-native prompt is already pending” and cannot report the policy that governed admission.

**Migration**: Replace non-forced calls with `admission_policy=ready_only`, replace calls that intend to queue only onto an empty provider queue with `admission_policy=if_no_pending`, and replace unconditional TUI calls with `admission_policy=always`. Update CLI calls from `--force` to `--admission-policy always`. No compatibility shim is provided.
