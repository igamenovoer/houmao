# Spec Delta

## MODIFIED Requirements

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

For TUI-backed targets, `POST /v1/control/prompt` SHALL accept `chat_session.mode = new` and SHALL reject `chat_session.mode = auto | current | tool_last_or_new | exact` with validation semantics rather than ignoring the field.

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
- **WHEN** a caller submits `POST /v1/control/prompt` for a native headless gateway target with `chat_session.mode = tool_last_or_new`
- **THEN** the gateway resolves that request by asking the tool to resume its latest stored chat or start fresh if none exists
- **AND THEN** the gateway does not reinterpret that selector as the managed agent's current pinned session

#### Scenario: TUI direct prompt control accepts explicit new-session reset request
- **WHEN** a caller submits `POST /v1/control/prompt` for a TUI-backed gateway target with `chat_session.mode = new`
- **THEN** the gateway accepts that request as a TUI conversation-reset workflow
- **AND THEN** it does not reinterpret that selector as headless provider-session state

#### Scenario: TUI direct prompt control rejects unsupported explicit session selector
- **WHEN** a caller submits `POST /v1/control/prompt` for a TUI-backed gateway target with `chat_session.mode = current`
- **THEN** the gateway rejects that request with validation semantics
- **AND THEN** it does not ignore the selector and pretend that ordinary prompt control succeeded
