## 1. Gateway Contracts

- [x] 1.1 Replace the headless prompt-control string selector with a structured `chat_session` request model and shared validation helpers.
- [x] 1.2 Extend gateway headless control-state models and routes to expose `chat_session.current`, `chat_session.startup_default`, and `chat_session.next_prompt_override`.
- [x] 1.3 Add `POST /v1/control/headless/next-prompt-session` with `mode = new` and return the updated headless control-state payload.

## 2. Gateway Runtime Behavior

- [x] 2.1 Implement headless selector normalization for `auto`, `new`, `current`, `tool_last_or_new`, and `exact` in immediate prompt-control admission.
- [x] 2.2 Implement `auto` resolution precedence, current-session pinning after successful turns, and explicit failure when `current` is requested without a pinned current session.
- [x] 2.3 Track the one-shot next-prompt override as live gateway state, consume it only on the next accepted auto prompt, and clear it on restart.
- [x] 2.4 Implement TUI support for `chat_session.mode = new` as reset-then-wait-then-send, and reject all other explicit chat-session modes plus headless-only routes for TUI-backed or unsupported targets.

## 3. Server and Proxy Integration

- [x] 3.1 Extend Houmao server models and routes for managed-agent gateway headless state proxying and next-prompt override proxying.
- [x] 3.2 Extend managed headless turn submission to accept structured `chat_session` and preserve normalized selector intent across gateway-backed and direct fallback execution.
- [x] 3.3 Update managed-agent gateway prompt-control and passive proxy handling so structured headless selector semantics are forwarded without reinterpretation.

## 4. Verification and Docs

- [x] 4.1 Add unit and integration coverage for `auto`, `current`, `tool_last_or_new`, `exact`, one-shot override consumption, restart-loss behavior, and TUI `mode = new` reset-then-send behavior.
- [x] 4.2 Add proxy and server tests for unsupported TUI mode rejection, missing-gateway errors, and forwarded headless control-state payloads.
- [x] 4.3 Update gateway and server API docs to document the structured `chat_session` model, `auto` semantics, and the live-only behavior of `next-prompt-session`.
