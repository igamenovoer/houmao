## MODIFIED Requirements

### Requirement: Gateway exposes semantic prompt submission separately from raw send-keys control

For gateway-managed tmux-backed sessions, the gateway SHALL keep semantic prompt submission separate from raw key/control-input delivery.

The gateway SHALL expose two semantic prompt surfaces:

- `POST /v1/requests` as the queued gateway request surface for `submit_prompt` and `interrupt`
- `POST /v1/control/prompt` as the immediate prompt-control surface for "send now or refuse now" prompt dispatch

The gateway SHALL additionally expose a dedicated raw control-input endpoint for send-keys style delivery. That endpoint SHALL accept exact `<[key-name]>` control-input sequences using the same contract as the runtime tmux-control-input capability, including optional full-string literal escaping.

Both semantic gateway prompt surfaces SHALL treat the provided prompt body as literal text, SHALL NOT interpret `<[key-name]>` substrings as special keys, and SHALL automatically submit once at the end.

The dedicated raw control-input endpoint SHALL NOT enqueue a durable `submit_prompt` request, SHALL NOT claim that a managed prompt turn was submitted, and SHALL NOT trigger gateway prompt-submission tracking hooks by itself.

#### Scenario: Gateway direct prompt control returns immediate dispatch semantics

- **WHEN** a caller submits managed prompt work through `POST /v1/control/prompt`
- **THEN** the gateway returns success only after that prompt has been admitted for immediate live dispatch on the current target
- **AND THEN** the response does not pretend that the prompt was merely queued for later execution

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

## ADDED Requirements

### Requirement: Gateway direct prompt control only dispatches when the addressed agent is prompt-ready unless forced

For gateway-managed prompt control through `POST /v1/control/prompt`, the gateway SHALL reject prompt dispatch by default unless the addressed target is ready to accept a new prompt immediately.

For TUI-backed sessions, the direct prompt-control path SHALL evaluate prompt readiness from the gateway-owned TUI state and SHALL require at minimum:

- `turn.phase = "ready"`
- `surface.accepting_input = "yes"`
- `surface.editing_input = "no"`
- `surface.ready_posture = "yes"`
- `stability.stable = true`

When a parsed surface is available for that TUI state, the gateway SHALL additionally require `parsed_surface.business_state = "idle"` and `parsed_surface.input_mode = "freeform"` before treating the target as prompt-ready.

For native headless sessions, the direct prompt-control path SHALL require that authoritative runtime control is operable and that no active execution or active turn is already running for that managed session.

When the request sets `force = true`, the gateway MAY bypass those prompt-readiness checks, but it SHALL still reject unavailable, reconciliation-blocked, invalid, or unsupported-target requests explicitly.

#### Scenario: Prompt-ready TUI accepts immediate prompt control

- **WHEN** a caller submits `POST /v1/control/prompt` for a TUI-backed gateway target
- **AND WHEN** the gateway-owned TUI state reports a stable ready posture with no active editing state
- **THEN** the gateway dispatches the prompt immediately
- **AND THEN** the success response states that the prompt was sent

#### Scenario: Busy TUI refuses direct prompt control by default

- **WHEN** a caller submits `POST /v1/control/prompt` for a TUI-backed gateway target
- **AND WHEN** the gateway-owned TUI state does not satisfy the prompt-ready contract
- **AND WHEN** the request does not set `force = true`
- **THEN** the gateway rejects that prompt explicitly
- **AND THEN** it does not return a success payload claiming the prompt was sent

#### Scenario: Force bypasses prompt-readiness refusal but not gateway availability failures

- **WHEN** a caller submits `POST /v1/control/prompt` with `force = true`
- **AND WHEN** the addressed target is connected but not currently prompt-ready
- **THEN** the gateway may dispatch the prompt anyway
- **AND THEN** the same route still rejects unavailable or reconciliation-blocked gateway state explicitly

#### Scenario: Headless prompt control rejects overlapping work

- **WHEN** a caller submits `POST /v1/control/prompt` for a native headless gateway target
- **AND WHEN** that target already has active execution in flight
- **THEN** the gateway rejects that prompt explicitly
- **AND THEN** it does not start overlapping headless prompt work

#### Scenario: Unsupported backend rejects direct prompt control explicitly

- **WHEN** a caller submits `POST /v1/control/prompt` for backend `codex_app_server`
- **THEN** the gateway rejects that request as not implemented
- **AND THEN** it does not pretend that prompt readiness was evaluated successfully

### Requirement: Gateway raw send-keys bypasses prompt-readiness and busy gating

For gateway-managed raw control input through `POST /v1/control/send-keys`, the gateway SHALL forward the exact control-input request without first requiring that the addressed agent is idle, stable, or prompt-ready.

The route MAY still reject the request for ordinary gateway availability failures such as detached gateway state, reconciliation blocking, or invalid control-input payloads.

#### Scenario: Raw send-keys still forwards while the TUI is busy

- **WHEN** a caller submits `POST /v1/control/send-keys` while the gateway-owned TUI state reports active work
- **THEN** the gateway forwards that raw control-input request immediately
- **AND THEN** it does not reject the request only because the agent is not prompt-ready
