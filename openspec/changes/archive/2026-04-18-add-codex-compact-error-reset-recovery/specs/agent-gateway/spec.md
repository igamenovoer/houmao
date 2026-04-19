## MODIFIED Requirements

### Requirement: Gateway direct prompt control only dispatches when the addressed agent is prompt-ready unless forced

For gateway-managed prompt control through `POST /v1/control/prompt`, the gateway SHALL reject prompt dispatch by default unless the addressed target is ready to accept a new prompt immediately.

For TUI-backed sessions, the direct prompt-control path SHALL evaluate prompt readiness from the gateway-owned TUI state and SHALL require at minimum:

- `turn.phase = "ready"`
- `surface.accepting_input = "yes"`
- `surface.editing_input = "no"`
- `surface.ready_posture = "yes"`
- `stability.stable = true`

When a parsed surface is available for that TUI state, the gateway SHALL additionally require `parsed_surface.business_state = "idle"` and `parsed_surface.input_mode = "freeform"` before treating the target as prompt-ready.

Previous-turn error evidence or current-error diagnostics SHALL NOT by themselves make a TUI-backed target non-ready when the prompt-ready contract above is satisfied.

For TUI-backed sessions with chat-context state `reset_required`, the direct prompt-control path SHALL accept the next prompt when the input surface is prompt-ready and SHALL normalize that prompt to effective `chat_session.mode = new`. Because TUI `chat_session.mode = new` is a gateway reset-then-send workflow rather than a provider-session selector, the gateway SHALL send a tool-appropriate context-reset signal before sending the caller's actual prompt.

For native headless sessions, the direct prompt-control path SHALL require that authoritative runtime control is operable and that no active execution or active turn is already running for that managed session.

For native headless sessions with chat-context state `reset_required`, the next accepted prompt SHALL begin with clean context. The gateway SHALL normalize the effective chat-session selector for that prompt to fresh provider-chat bootstrap and SHALL include `chat_session.mode = new` in the dispatched request body.

Malformed `chat_session` payloads SHALL still be rejected with validation semantics. Otherwise, the reset-required `chat_session.mode = new` normalization SHALL take precedence over ordinary continuity selectors for the accepted prompt.

For TUI-backed sessions with `chat_session.mode = new` or chat-context state `reset_required`, the direct prompt-control path SHALL:

- require an initial prompt-ready TUI posture suitable for semantic reset submission,
- send a tool-appropriate semantic context-reset signal,
- use `/new` as the context-reset signal for Codex TUI targets,
- allow other TUI targets to use their configured reset signal such as `/clear`,
- wait until the tracked TUI state stabilizes back to prompt-ready posture without chat-context state `reset_required`,
- send the caller's actual prompt only after that post-reset stabilization succeeds.

If the TUI target lacks a supported reset workflow, if the reset signal cannot be admitted, or if post-reset stabilization does not succeed, the gateway SHALL fail the request explicitly and SHALL NOT claim that the caller's actual prompt was delivered.

For native headless sessions without chat-context state `reset_required`, the gateway SHALL resolve the effective chat-session selector as follows:

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

When the request sets `force = true`, the gateway MAY bypass prompt-readiness checks, but it SHALL still reject unavailable, reconciliation-blocked, invalid-selector, incompatible-target, or unsupported-target requests explicitly. For reset-required targets, `force = true` SHALL NOT bypass clean-context enforcement.

#### Scenario: Prompt-ready TUI accepts immediate prompt control

- **WHEN** a caller submits `POST /v1/control/prompt` for a TUI-backed gateway target
- **AND WHEN** the gateway-owned TUI state reports a stable ready posture with no active editing state
- **AND WHEN** chat-context state is not `reset_required`
- **THEN** the gateway dispatches the prompt immediately
- **AND THEN** the success response states that the prompt was sent

#### Scenario: Busy TUI refuses direct prompt control by default

- **WHEN** a caller submits `POST /v1/control/prompt` for a TUI-backed gateway target
- **AND WHEN** the gateway-owned TUI state does not satisfy the prompt-ready contract
- **AND WHEN** the request does not set `force = true`
- **THEN** the gateway rejects that prompt explicitly
- **AND THEN** it does not return a success payload claiming the prompt was sent

#### Scenario: Prompt-ready generic error surface accepts ordinary prompt control
- **WHEN** a caller submits `POST /v1/control/prompt` for a TUI-backed gateway target without `chat_session.mode = new`
- **AND WHEN** the gateway-owned TUI state satisfies the prompt-ready contract while also reporting previous-turn generic error evidence
- **AND WHEN** chat-context state is not `reset_required`
- **THEN** the gateway dispatches the prompt immediately
- **AND THEN** it does not reject the prompt solely because the previous visible turn contains a generic error

#### Scenario: Prompt-ready reset-required TUI resets before prompt control
- **WHEN** a caller submits `POST /v1/control/prompt` for a TUI-backed gateway target without `chat_session.mode = new`
- **AND WHEN** the gateway-owned TUI state satisfies the prompt-ready contract and chat-context state is `reset_required`
- **THEN** the gateway treats the prompt as an implicit TUI `chat_session.mode = new` request and sends the tool-appropriate context-reset signal before the caller's prompt
- **AND THEN** after the TUI stabilizes back to ready posture without chat-context state `reset_required`, the gateway sends the caller's actual prompt

#### Scenario: Reset-required headless prompt uses request-body clean-context selector
- **WHEN** a caller submits `POST /v1/control/prompt` for a native headless gateway target
- **AND WHEN** the gateway-owned state has chat-context state `reset_required`
- **THEN** the gateway accepts the prompt only by normalizing the effective chat-session selector to `chat_session.mode = new`
- **AND THEN** the dispatched request body carries that clean-context selector

#### Scenario: Reset-required headless override takes precedence over ordinary continuity
- **WHEN** a caller submits `POST /v1/control/prompt` for a native headless gateway target with omitted `chat_session` or an otherwise reusable continuity selector
- **AND WHEN** the gateway-owned state has chat-context state `reset_required`
- **THEN** the gateway resolves the accepted prompt as clean-context execution with effective `chat_session.mode = new`
- **AND THEN** it does not reuse `chat_session.current`, `chat_session.next_prompt_override`, tool-latest storage, or an exact stale provider session for that prompt

#### Scenario: TUI new mode resets the conversation before sending the prompt
- **WHEN** a caller submits `POST /v1/control/prompt` for a TUI-backed gateway target with `chat_session.mode = new`
- **AND WHEN** the gateway-owned TUI state reports a stable ready posture
- **THEN** the gateway first sends the configured tool-appropriate context-reset signal
- **AND THEN** after the TUI stabilizes back to ready posture without chat-context state `reset_required`, the gateway sends the caller's actual prompt

#### Scenario: Codex TUI clean-context reset uses slash-new
- **WHEN** a caller submits prompt work for a Codex TUI-backed gateway target and the gateway must begin with clean context
- **AND WHEN** the gateway-owned TUI state reports a stable ready posture
- **THEN** the gateway sends `/new` as the semantic context-reset signal
- **AND THEN** it does not use `/clear` as the Codex context-reset signal for this workflow

#### Scenario: Generic TUI reset may use slash-clear
- **WHEN** a caller submits prompt work for a non-Codex TUI-backed gateway target and the gateway must begin with clean context
- **AND WHEN** that target's configured context-reset signal is `/clear`
- **THEN** the gateway sends `/clear` as the semantic context-reset signal
- **AND THEN** it still waits for post-reset prompt-ready stabilization before sending the caller's actual prompt

#### Scenario: TUI reset fails when post-reset stabilization does not complete
- **WHEN** a caller submits prompt work that requires a TUI context reset
- **AND WHEN** the reset signal is sent but the TUI does not stabilize back to ready posture without chat-context state `reset_required` within the allowed wait
- **THEN** the gateway rejects that request explicitly
- **AND THEN** it does not claim that the caller's actual prompt was delivered

#### Scenario: Generic unknown state does not admit prompt control
- **WHEN** a caller submits `POST /v1/control/prompt` for a TUI-backed gateway target
- **AND WHEN** the gateway-owned TUI state lacks the prompt-ready contract
- **THEN** the gateway rejects the request explicitly unless `force = true` is used
- **AND THEN** it does not infer prompt readiness from reset-required diagnostics or generic unknown posture alone

#### Scenario: Force bypasses prompt-readiness refusal but not clean-context enforcement

- **WHEN** a caller submits `POST /v1/control/prompt` with `force = true`
- **AND WHEN** the addressed target is connected but not currently prompt-ready
- **THEN** the gateway may dispatch the prompt anyway
- **AND THEN** the same route still rejects unavailable or reconciliation-blocked gateway state explicitly
- **AND THEN** if chat-context state is `reset_required`, the accepted prompt still begins with clean context

#### Scenario: Headless prompt control rejects overlapping work

- **WHEN** a caller submits `POST /v1/control/prompt` for a native headless gateway target
- **AND WHEN** that target already has active execution in flight
- **THEN** the gateway rejects that prompt explicitly
- **AND THEN** it does not start overlapping headless prompt work

#### Scenario: Auto mode prefers the managed agent's current pinned session
- **WHEN** a caller submits `POST /v1/control/prompt` for a native headless gateway target with omitted `chat_session`
- **AND WHEN** that managed agent already has `chat_session.current`
- **AND WHEN** chat-context state is not `reset_required`
- **THEN** the gateway resolves that prompt against the pinned current provider session
- **AND THEN** it does not re-query the tool's global latest-session storage for that prompt

#### Scenario: Current mode fails when no pinned current session exists
- **WHEN** a caller submits `POST /v1/control/prompt` for a native headless gateway target with `chat_session.mode = current`
- **AND WHEN** the managed agent does not have `chat_session.current`
- **AND WHEN** chat-context state is not `reset_required`
- **THEN** the gateway rejects that request explicitly
- **AND THEN** it does not silently fall back to `auto`, startup default, or fresh bootstrap

#### Scenario: Unsupported backend rejects direct prompt control explicitly

- **WHEN** a caller submits `POST /v1/control/prompt` for backend `codex_app_server`
- **THEN** the gateway rejects that request as not implemented
- **AND THEN** it does not pretend that prompt readiness was evaluated successfully
