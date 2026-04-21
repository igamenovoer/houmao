## 1. Degraded Diagnostic Model

- [x] 1.1 Add shared tracked-state diagnostic fields for degraded chat context, including owning tool/profile identity and tool-scoped degraded error type.
- [x] 1.2 Extend Codex TUI compact/server error classification to emit Codex-owned degraded error types such as `codex_remote_compact_stream_disconnected`, `codex_remote_compact_context_length_exceeded`, and `codex_remote_compact_unknown_parameter`.
- [x] 1.3 Ensure `unknown` remains the only shared degraded error type fallback and add tests proving non-Codex tools do not inherit Codex-specific labels.
- [x] 1.4 Preserve bounded prompt-adjacent matching so historical compact/server errors do not create current degraded diagnostics.

## 2. Notifier Policy State And API

- [x] 2.1 Extend gateway notifier request/status models with `context_error_policy` and `pre_notification_context_action` defaults.
- [x] 2.2 Extend gateway-owned notifier storage to persist the new policy fields with backward-compatible defaults for existing rows.
- [x] 2.3 Update direct gateway `/v1/mail-notifier` and server-managed mail-notifier proxy behavior to read, write, and report the same policy state.
- [x] 2.4 Update `houmao-mgr agents gateway mail-notifier enable|status` options, rendering, and help text for the new policy fields.

## 3. Notifier Context Preflight

- [x] 3.1 Add notifier support checks for `pre_notification_context_action=compact`, accepting only CLI tool/backend combinations with a supported compaction preflight.
- [x] 3.2 Implement Codex TUI pre-notification compaction by submitting `/compact`, waiting for prompt-ready stabilization, refreshing tracked diagnostics, and auditing the result.
- [x] 3.3 Reject or report unsupported `compact` policy explicitly for tools and backend modes without a defined compaction preflight.
- [x] 3.4 Ensure failed compaction preflight does not mark, move, answer, or archive mailbox messages.

## 4. Policy-Selected Clean Context

- [x] 4.1 Add notifier decision logic that chooses clean-context delivery only when `context_error_policy=clear_context` and the current degraded diagnostic is a recognized compaction error for the owning CLI tool.
- [x] 4.2 Reuse existing gateway clean-context prompt-control behavior for policy-selected notifier prompts, including Codex TUI reset-then-send and supported headless fresh-chat selection.
- [x] 4.3 Preserve default `continue_current` behavior for degraded compaction diagnostics and generic current-error diagnostics.
- [x] 4.4 Add regression tests showing degraded context alone does not clear context, while explicit policy plus recognized compaction diagnostic does.

## 5. Audit And Observability

- [x] 5.1 Extend notifier audit records with effective context policies, compaction preflight attempt/result, clean-context recovery attempt/result, owning tool, degraded error type, and failure detail.
- [x] 5.2 Ensure audit outcomes do not claim clean-context success unless a clean-context workflow completed and the notifier prompt was accepted afterward.
- [x] 5.3 Add status or audit inspection coverage for policy defaults, explicit policy configuration, unsupported compact policy, compaction failure, and clean-context recovery failure.

## 6. Documentation And Skills

- [x] 6.1 Update gateway mail-notifier reference documentation with the new policies, defaults, support boundaries, and continuity trade-offs.
- [x] 6.2 Update gateway protocol/state documentation to describe policy-selected clean-context delivery separately from degraded context diagnostics.
- [x] 6.3 Update TUI tracking documentation to state that degraded error types are tool-scoped and that only `unknown` is shared across CLI tools.
- [x] 6.4 Update relevant Houmao system skill guidance for gateway mail-notifier enable/status usage without implying automatic reset by default.

## 7. Verification

- [x] 7.1 Add focused unit tests for Codex-specific degraded diagnostic classification.
- [x] 7.2 Add gateway notifier unit tests for default policy preservation, explicit policy persistence, pre-notification compaction, unsupported compact policy, and policy-selected clean-context recovery.
- [x] 7.3 Add CLI rendering/help tests for new mail-notifier options.
- [x] 7.4 Run `pixi run test` and any narrower affected test modules needed for gateway and shared TUI tracking changes.
