## 1. Tracking Semantics

- [x] 1.1 Replace mandatory `reset_required` chat-context semantics with recoverable degraded-context semantics in shared tracked-state models and public payloads.
- [x] 1.2 Update Codex compact/server error notes and helper names so they no longer imply a required context reset.
- [x] 1.3 Keep Codex compact/server error detection bounded to the prompt-adjacent prompt region and ensure long scrollback errors do not affect current state.
- [x] 1.4 Ensure prompt-adjacent compact/server errors set current-error evidence, block success candidacy, and preserve prompt-ready input posture when composer facts are ready.

## 2. Live TUI Recovery

- [x] 2.1 Verify final stable-active recovery applies to stable promptable degraded error surfaces with submit-ready parsed-surface evidence.
- [x] 2.2 Ensure recovery publishes `turn.phase=ready` and prompt-ready surface posture without setting `last_turn.result=success` or `known_failure`.
- [x] 2.3 Preserve degraded/error diagnostics after recovery so operators can still see that the current context is recoverable but unhealthy.

## 3. Gateway Prompt Control

- [x] 3.1 Remove automatic headless selector normalization from degraded context to `chat_session.mode = new`.
- [x] 3.2 Remove automatic TUI reset-then-send dispatch from degraded context.
- [x] 3.3 Preserve explicit `chat_session.mode = new` behavior for supported headless and TUI-backed prompt control.
- [x] 3.4 Ensure TUI post-reset stabilization no longer waits for degraded context to clear unless the reset was explicitly requested and the remaining blockers are actual prompt-readiness blockers.

## 4. Mail Notifier

- [x] 4.1 Update notifier eligibility so prompt-ready degraded sessions are not busy-skipped solely because degraded context is present.
- [x] 4.2 Update notifier dispatch so degraded context uses ordinary current-context prompt work instead of clean-context enqueue or TUI reset.
- [x] 4.3 Update notifier audit outcomes/details so clean-context outcomes are recorded only when an explicit clean-context workflow actually runs.

## 5. Regression Coverage and Validation

- [x] 5.1 Add Codex detector tests for prompt-adjacent compact/server errors, generic prompt-adjacent errors, and historical scrollback compact errors.
- [x] 5.2 Add live tracking regression coverage for stable false-active recovery on a promptable degraded compact-error surface.
- [x] 5.3 Add gateway prompt-control tests proving degraded context does not force reset and explicit `chat_session.mode = new` still resets.
- [x] 5.4 Add mail notifier tests proving degraded context enqueues current-context notifier work without reset.
- [x] 5.5 Run targeted unit tests, `pixi run lint`, and OpenSpec validation for this change.
