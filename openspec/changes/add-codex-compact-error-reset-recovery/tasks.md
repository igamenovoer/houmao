## 1. Codex TUI State Semantics

- [ ] 1.1 Update Codex TUI reduction so current error evidence blocks success settlement without forcing prompt-ready composer facts to unknown.
- [ ] 1.2 Add prompt-adjacent compact/server-error detection that emits chat-context state `reset_required` separate from prompt readiness, success, and known-failure state.
- [ ] 1.3 Ensure generic red errors that do not match the reset-required signature never emit chat-context state `reset_required`.
- [ ] 1.4 Add unit coverage for prompt-ready generic error surfaces, prompt-ready reset-required compact/server-error surfaces, historical scrollback errors outside the live edge, active-turn blockers, overlays, and prompt drafts.

## 2. Gateway Clean-Context Prompt Control

- [ ] 2.1 Ensure gateway prompt-readiness refusal does not treat previous-turn error diagnostics as an independent not-ready reason when prompt-ready fields are satisfied.
- [ ] 2.2 Make native headless prompt control normalize the effective request-body selector to `chat_session.mode = new` when chat-context state is `reset_required`.
- [ ] 2.3 Make TUI prompt control treat `reset_required` as an implicit `chat_session.mode = new` request, sending the tool-appropriate context-reset signal before the caller's prompt.
- [ ] 2.4 Add tool-aware TUI reset signal selection so Codex clean-context prompts use `/new` and configured non-Codex resets can use `/clear`.
- [ ] 2.5 Preserve post-reset prompt-ready stabilization and require `reset_required` to clear before sending a TUI caller's actual prompt.
- [ ] 2.6 Add gateway prompt-control tests for prompt-ready generic error dispatch, reset-required headless request-body override, reset-required TUI reset-then-send, Codex `/new`, configured `/clear`, force still enforcing clean context, and post-reset failure.

## 3. Mail Notifier Clean-Context Recovery and Audit

- [ ] 3.1 Update notifier eligibility so prompt-ready `reset_required` sessions do not busy-skip solely because context reset is required.
- [ ] 3.2 For headless notifier work, include `chat_session.mode = new` in the request body when chat-context state is `reset_required`.
- [ ] 3.3 For TUI notifier work, treat `reset_required` as implicit `chat_session.mode = new`, run the tool-appropriate reset signal, wait for prompt-ready stabilization without `reset_required`, then preserve existing queue-admission and notifier prompt rules.
- [ ] 3.4 Record structured audit outcomes for clean-context notification success and reset failure.
- [ ] 3.5 Ensure reset failure does not enqueue notifier work or mutate mailbox read, answered, archived, or closed state.
- [ ] 3.6 Add notifier tests for reset-required headless clean-context selection, reset-required TUI recovery, Codex `/new`, configured `/clear`, reset failure, prompt-ready generic-error notification without reset, generic not-ready busy skip, and mailbox-state preservation.

## 4. Verification

- [ ] 4.1 Run targeted Codex TUI state-tracking tests.
- [ ] 4.2 Run targeted gateway prompt-control and mail-notifier tests.
- [ ] 4.3 Run `pixi run test` or document any narrower verification used when the full suite is impractical.
