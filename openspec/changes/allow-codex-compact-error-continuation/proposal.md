## Why

Recent OpenAI provider behavior changed the recovery envelope for Codex compaction errors: a prompt-adjacent compact/server error can still leave the Codex TUI promptable, and a follow-up prompt such as "continue" may recover without clearing chat context. Houmao should track that surface as prompt-ready but degraded, not force a context reset solely because the error text is visible.

## What Changes

- Replace the reset-first interpretation of prompt-adjacent Codex compact/server errors with a recoverable degraded-context interpretation.
- Keep prompt readiness separate from error evidence: a stable ready composer with a current prompt-adjacent error remains promptable, while the error still blocks success settlement.
- Restrict compact/server error classification to the prompt-adjacent live prompt region so historical error text in long scrollback cannot affect current state.
- Stop gateway prompt control from implicitly converting degraded-context prompts into `chat_session.mode = new`; ordinary prompts continue in the current chat context.
- Preserve explicit clean-context behavior: callers may still request `chat_session.mode = new`, and TUI targets still handle that as the existing reset-then-send workflow.
- Stop the gateway mail notifier from implicitly resetting degraded prompt-ready sessions; notifier prompts should use the same current-context path as ordinary prompt work when all readiness and queue gates pass.
- Ensure the stable false-active safeguard recovers prompt-ready compact-error surfaces from `turn.phase=active` to non-active ready state after the configured dwell, without manufacturing success.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `codex-tui-state-tracking`: compact/server error cells near the prompt become recoverable degraded-context evidence, not a forced reset requirement, while continuing to block success.
- `official-tui-state-tracking`: prompt-ready degraded error surfaces remain eligible for ready/non-active state, including stable false-active recovery to ready without success.
- `agent-gateway`: degraded chat context does not implicitly select `chat_session.mode = new`; only explicit clean-context requests reset.
- `agent-gateway-mail-notifier`: prompt-ready degraded sessions are not busy-skipped or reset solely because degraded context is present; notifier work continues in current context unless explicitly configured otherwise.

## Impact

- Affected code includes Codex TUI error classification and chat-context notes under `src/houmao/shared_tui_tracking/apps/codex_tui/`, shared tracked-state models, live TUI tracking recovery under `src/houmao/server/tui/tracking.py`, and gateway prompt/notifier reset handling under `src/houmao/agents/realm_controller/gateway_service.py`.
- Existing explicit `chat_session.mode = new` behavior remains supported for headless and TUI-backed prompt control.
- This change supersedes the automatic reset semantics introduced by `add-codex-compact-error-reset-recovery`; implementation should remove or rename `reset_required` rather than keeping a field name that implies mandatory reset.
- No new external dependency or persisted user-data migration is required.
