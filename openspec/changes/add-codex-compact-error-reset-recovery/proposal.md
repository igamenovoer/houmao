## Why

Issue 19 exposes two separate states that must be modeled independently:

- the Codex TUI input surface can be prompt-ready after a compact/server error because the user can type and submit another prompt, and
- the current chat context can still require a reset before the next semantic prompt should run.

Today Houmao effectively mixes these concerns by letting a visible error surface push the tracked posture into unknown readiness. That causes the gateway mail notifier to busy-skip even when the composer can accept input, while still failing to represent the real problem: the next prompt must begin with clean context, using a request-body clean-context selector for headless targets or a clear/reset signal before prompt submission for TUI targets.

## What Changes

- Introduce a `reset_required` chat-context state for prompt-adjacent compact/server-error surfaces that indicate the next semantic prompt must begin with clean context.
- Keep prompt readiness as input-surface state: a stable ready composer can remain prompt-ready while chat context is `reset_required`.
- Preserve prompt-adjacent error correctness separately: current red error cells still block success settlement, and historical error text in long scrollback is ignored when deriving current error or `reset_required` state.
- Update gateway prompt control so the next accepted semantic prompt consumes `reset_required` by normalizing the effective chat-session selector to `chat_session.mode = new`:
  - native headless dispatch carries that clean-context selector in the request body;
  - TUI dispatch treats that selector as the existing reset-then-send workflow, sends the tool-appropriate clear/reset signal first, waits for prompt readiness without `reset_required`, then sends the caller's prompt.
- Update the mail notifier so prompt-ready `reset_required` sessions are not busy-skipped; the notifier uses the same clean-context path before enqueueing or delivering the notifier prompt, with explicit audit evidence.
- Preserve conservative behavior for genuinely non-ready states such as active turns, blocking overlays, prompt drafts, detached sessions, queued work, and unknown composer posture.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `codex-tui-state-tracking`: separate input readiness from current error evidence and expose a prompt-adjacent `reset_required` chat-context state without forcing prompt readiness to unknown.
- `agent-gateway`: make the next accepted semantic prompt normalize to effective `chat_session.mode = new` when chat context is `reset_required`, using request-body chat-session selection for headless targets and reset-then-send workflow semantics for TUI targets.
- `agent-gateway-mail-notifier`: recover prompt-ready `reset_required` sessions through the same clean-context prompt path and audit the outcome.

## Impact

- Affected code includes Codex TUI signal/profile reduction under `src/houmao/shared_tui_tracking/apps/codex_tui/`, gateway prompt/reset control under `src/houmao/agents/realm_controller/gateway_service.py`, gateway notifier eligibility/audit behavior, and related unit coverage.
- No new external dependency is required.
- Public behavior changes for prompt-ready sessions whose chat context is `reset_required`: Houmao no longer reports them as merely non-ready, and the next semantic prompt begins with clean context automatically.
