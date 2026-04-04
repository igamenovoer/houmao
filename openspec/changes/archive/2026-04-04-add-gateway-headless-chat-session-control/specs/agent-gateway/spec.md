## ADDED Requirements

### Requirement: Gateway exposes explicit headless chat-session state and next-prompt override control
For native headless gateway targets, the live gateway SHALL expose dedicated headless chat-session control routes:

- `GET /v1/control/headless/state`
- `POST /v1/control/headless/next-prompt-session`

`GET /v1/control/headless/state` SHALL return the gateway's current headless control-state payload for the addressed managed session.

That payload SHALL include a `chat_session` state object with at least:

- `current`, describing the concrete provider session currently pinned by the managed agent or `null` when none is pinned
- `startup_default`, describing the managed agent's first-chat fallback policy using one of `new`, `tool_last_or_new`, or `exact`
- `next_prompt_override`, containing either `null` or a one-shot override object

When `startup_default.mode = exact`, the state payload SHALL include the exact provider session id used by that startup default.

In this change, `POST /v1/control/headless/next-prompt-session` SHALL be valid only for native headless gateway targets and SHALL accept only `mode = new`. It SHALL set `chat_session.next_prompt_override` so the next accepted prompt whose effective selector is `auto` uses a fresh provider chat.

That one-shot override SHALL:

- be gateway-local live state rather than durable persisted state,
- be lost if the gateway stops or restarts,
- be consumed only when the next accepted `auto` prompt is admitted,
- remain pending when a later prompt explicitly requests `new`, `current`, `tool_last_or_new`, or `exact`,
- not affect queued gateway requests, wakeup delivery, mail-notifier behavior, or other internal gateway-generated prompts.

`POST /v1/control/headless/next-prompt-session` SHALL return the updated headless control-state payload after storing the pending override.

For TUI-backed or otherwise non-headless targets, both routes SHALL reject the request with validation semantics rather than pretending that a headless control surface exists.

#### Scenario: Headless state reports current session, startup default, and pending override
- **WHEN** a caller requests `GET /v1/control/headless/state` for a native headless gateway target
- **THEN** the response includes `chat_session.current`, `chat_session.startup_default`, and `chat_session.next_prompt_override`
- **AND THEN** the caller can distinguish the managed agent's pinned current session from its startup policy and one-shot override posture

#### Scenario: Next-prompt override is consumed by the next accepted auto prompt
- **WHEN** a caller first submits `POST /v1/control/headless/next-prompt-session` with `mode = new`
- **AND WHEN** the next accepted public `POST /v1/control/prompt` for that same headless target omits `chat_session` or explicitly sets `chat_session.mode = auto`
- **THEN** that prompt uses a fresh provider chat
- **AND THEN** a later `GET /v1/control/headless/state` no longer reports a pending next-prompt override

#### Scenario: Explicit non-auto prompt does not consume the pending next-prompt override
- **WHEN** a caller first submits `POST /v1/control/headless/next-prompt-session` with `mode = new`
- **AND WHEN** a later accepted `POST /v1/control/prompt` for that same headless target explicitly requests `chat_session.mode = current`
- **THEN** the gateway resolves that prompt using the explicit selector
- **AND THEN** the pending next-prompt override remains visible until a later accepted auto prompt consumes it or the gateway stops

#### Scenario: Restart clears the pending next-prompt override
- **WHEN** a native headless gateway target has a pending next-prompt override
- **AND WHEN** the gateway stops or restarts before an accepted auto prompt consumes it
- **THEN** the restarted gateway no longer reports that pending override
- **AND THEN** the override is not recovered from durable gateway state

#### Scenario: TUI target rejects headless chat-session control routes
- **WHEN** a caller requests `GET /v1/control/headless/state` or `POST /v1/control/headless/next-prompt-session` for a TUI-backed gateway target
- **THEN** the gateway rejects that request with validation semantics
- **AND THEN** it does not pretend that a headless control surface exists for that target

## MODIFIED Requirements

### Requirement: Gateway exposes semantic prompt submission separately from raw send-keys control

For gateway-managed tmux-backed sessions, the gateway SHALL keep semantic prompt submission separate from raw key/control-input delivery.

The gateway SHALL expose two semantic prompt surfaces:

- `POST /v1/requests` as the queued gateway request surface for `submit_prompt` and `interrupt`
- `POST /v1/control/prompt` as the immediate prompt-control surface for "send now or refuse now" prompt dispatch

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

For TUI-backed sessions with `chat_session.mode = new`, the direct prompt-control path SHALL:

- require an initial prompt-ready TUI posture suitable for semantic prompt submission,
- send a semantic reset prompt such as `/clear`,
- wait until the tracked TUI state stabilizes back to prompt-ready posture,
- send the caller's actual prompt only after that post-reset stabilization succeeds.

If the TUI target lacks a supported reset workflow, if the reset prompt cannot be admitted, or if post-reset stabilization does not succeed, the gateway SHALL fail the request explicitly and SHALL NOT claim that the caller's actual prompt was delivered.

For native headless sessions, the gateway SHALL resolve the effective chat-session selector as follows:

- `chat_session.mode = auto` resolves in this order:
  - `chat_session.next_prompt_override` when present,
  - `chat_session.current` when present,
  - `chat_session.startup_default`,
  - `new`
- `chat_session.mode = current` requires `chat_session.current` to exist and SHALL fail explicitly when no current session is pinned
- `chat_session.mode = tool_last_or_new` asks the tool to resume its latest stored chat and falls back to fresh if none exists
- `chat_session.mode = exact` uses the provided exact provider session id
- `chat_session.mode = new` forces fresh provider-chat bootstrap

After a successful headless prompt turn, the resolved concrete provider session id returned by the tool SHALL become the managed agent's `chat_session.current` when one is reported.

When the request sets `force = true`, the gateway MAY bypass readiness checks, but it SHALL still reject unavailable, reconciliation-blocked, invalid-selector, incompatible-target, or unsupported-target requests explicitly.

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

#### Scenario: TUI new mode clears the conversation before sending the prompt
- **WHEN** a caller submits `POST /v1/control/prompt` for a TUI-backed gateway target with `chat_session.mode = new`
- **AND WHEN** the gateway-owned TUI state reports a stable ready posture
- **THEN** the gateway first sends the configured reset prompt such as `/clear`
- **AND THEN** after the TUI stabilizes back to ready posture, the gateway sends the caller's actual prompt

#### Scenario: TUI new mode fails when post-clear stabilization does not complete
- **WHEN** a caller submits `POST /v1/control/prompt` for a TUI-backed gateway target with `chat_session.mode = new`
- **AND WHEN** the reset prompt is sent but the TUI does not stabilize back to ready posture within the allowed wait
- **THEN** the gateway rejects that request explicitly
- **AND THEN** it does not claim that the caller's actual prompt was delivered

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

#### Scenario: Auto mode prefers the managed agent's current pinned session
- **WHEN** a caller submits `POST /v1/control/prompt` for a native headless gateway target with omitted `chat_session`
- **AND WHEN** that managed agent already has `chat_session.current`
- **THEN** the gateway resolves the prompt against that pinned current session
- **AND THEN** it does not ask the tool to rediscover its own latest stored chat for that prompt

#### Scenario: Tool-native latest selection becomes the managed agent's current session after success
- **WHEN** a caller submits `POST /v1/control/prompt` for a native headless gateway target with `chat_session.mode = tool_last_or_new`
- **AND WHEN** the tool successfully resumes or creates a concrete provider session for that prompt
- **THEN** the gateway records that concrete provider session as `chat_session.current`
- **AND THEN** later `auto` prompts continue from that pinned current session unless another selector changes it

#### Scenario: Current mode fails explicitly when no current session is pinned
- **WHEN** a caller submits `POST /v1/control/prompt` for a native headless gateway target with `chat_session.mode = current`
- **AND WHEN** that managed agent has no pinned current session
- **THEN** the gateway rejects the request explicitly
- **AND THEN** it does not silently fall back to auto or fresh bootstrap

#### Scenario: Unsupported backend rejects direct prompt control explicitly

- **WHEN** a caller submits `POST /v1/control/prompt` for backend `codex_app_server`
- **THEN** the gateway rejects that request as not implemented
- **AND THEN** it does not pretend that prompt readiness was evaluated successfully
