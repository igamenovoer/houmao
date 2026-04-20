## Context

Houmao already distinguishes prompt readiness from recoverable degraded chat context. The April 18 continuation change made prompt-adjacent Codex compact/server failures produce `chat_context=degraded` instead of mandatory reset behavior, and gateway prompt control plus mail notifier delivery now continue current-context work by default when the prompt surface is otherwise ready.

The upstream Codex compaction incidents add two new pressures. First, unattended mailbox workflows can hit the same context-pressure path repeatedly, so operators need an explicit way to reduce the likelihood of compaction failure before a notifier prompt lands. Second, some environments may prefer to sacrifice chat continuity after a recognized compaction failure, but that must be an explicit policy because automatic clear-context behavior can lose useful current-thread state.

The diagnostic vocabulary also needs to stay honest. A degraded error type is a CLI-tool-specific classification. Codex can classify Codex compact error surfaces, but those labels must not be reused as if they were stable Claude, Gemini, or generic Houmao labels. The only cross-tool fallback value is `unknown`.

## Goals / Non-Goals

**Goals:**

- Preserve the current default: recoverable degraded context remains promptable and current-context eligible.
- Add mail-notifier configuration for opt-in clear-context recovery when a recognized degraded compaction error is present.
- Add mail-notifier configuration for opt-in pre-notification compaction before sending the notifier prompt.
- Surface structured degraded-context diagnostics with tool identity and tool-scoped error types.
- Keep notifier audit records sufficient to explain whether compaction, clear-context recovery, or ordinary current-context delivery happened.
- Reject unsupported pre-notification compaction combinations explicitly.

**Non-Goals:**

- Do not reintroduce automatic reset solely because `chat_context=degraded` is present.
- Do not guarantee that pre-notification compaction prevents upstream Codex failures.
- Do not define one shared degraded error-type enum for every CLI tool.
- Do not mutate mailbox read, answered, moved, or archive state as a side effect of context recovery attempts.
- Do not require every backend to support `/compact` or equivalent context compaction in v1.

## Decisions

### Keep default behavior unchanged and policy-gate recovery

Notifier state gets two explicit policy fields:

- `context_error_policy`: `continue_current` by default, with opt-in `clear_context`.
- `pre_notification_context_action`: `none` by default, with opt-in `compact`.

`continue_current` means degraded diagnostics are reported but the notifier uses the same current-context path it uses today. `clear_context` means the notifier may consume a recognized degraded compaction diagnostic by using the existing clean-context prompt-control machinery before delivering the semantic notifier prompt.

Alternative considered: restore automatic clean-context behavior for all degraded context. That was rejected because the current provider behavior sometimes recovers by continuing and because existing specs intentionally classify this as degraded diagnostic evidence rather than mandatory reset.

### Make degraded diagnostics profile-owned and tool-scoped

The tracked-state diagnostic should carry at least:

- `tool`: the profile/tool that produced the diagnostic, such as `codex`;
- `kind`: a stable broad diagnostic family, such as degraded chat context;
- `degraded_error_type`: a tool-scoped string;
- optional bounded message preview or detail fields useful for debugging.

Codex-specific values should use Codex-owned labels such as `codex_remote_compact_stream_disconnected`, `codex_remote_compact_context_length_exceeded`, `codex_remote_compact_unknown_parameter`, and `codex_remote_compact_server_error`. Other tools must not reuse those labels unless they are actually reporting a Codex surface. They either define their own tool-prefixed values or report `unknown`.

Alternative considered: define shared labels like `stream_disconnected` or `context_length_exceeded`. That hides tool semantics inside generic labels and will create false equivalence across CLI tools whose errors, transport behavior, and recovery commands differ.

### Run pre-notification compaction as a preflight, not as the notifier prompt

When `pre_notification_context_action=compact`, the notifier should run the tool-supported compaction command before creating the mailbox-processing notifier prompt. For Codex TUI v1 this is `/compact`; the gateway waits for prompt-ready stabilization afterward, refreshes tracked state, records the outcome, and then proceeds according to the configured context-error policy.

If the compaction preflight itself produces degraded context, the notifier does not automatically clear context unless `context_error_policy=clear_context` is configured. With the default policy, it records the degraded diagnostic and still delivers the notifier prompt through current-context work if the prompt-ready and queue-admission gates pass.

Alternative considered: prepend `/compact` and the notifier prompt into one raw sequence. That would be less observable and harder to recover when compaction fails; keeping compaction as a preflight gives a clear audit point and avoids sending mailbox work while the surface is still busy.

### Limit v1 compaction support to known tool/backing combinations

The first implementation should support pre-notification compaction only where Houmao has a proven control primitive. Codex TUI can support `/compact`. Unsupported tools or headless modes should reject `pre_notification_context_action=compact` at configuration time or before the first poll with a clear support error.

This boundary is intentionally conservative. A future Claude, Gemini, or headless Codex implementation can define its own tool-specific compaction action and diagnostic labels later without changing the contract.

Alternative considered: silently ignore `compact` for unsupported tools. That would make the operator believe a risk-reduction policy is active when it is not.

### Reuse existing clean-context prompt control for policy-selected reset

When policy selects clean-context recovery, the notifier should reuse existing gateway prompt-control semantics:

- TUI-backed Codex uses the tool-appropriate reset signal, currently `/new`, waits for prompt-ready posture, then sends or enqueues the notifier prompt.
- Native headless targets use the explicit fresh chat selector where supported.

This recovery is allowed only because a configured policy requests it. It is not implied by degraded context alone.

Alternative considered: add a notifier-only reset path separate from prompt control. That would duplicate reset behavior and increase the chance of divergence between manual prompt control, reminders, and notifier-driven work.

### Audit policy decisions and recovery outcomes

Notifier audit should record context policy inputs and results in gateway-owned state. Useful fields include the effective policies, whether pre-notification compaction was attempted, whether clean-context recovery was attempted, the tool-scoped degraded diagnostic, and any recovery failure detail.

Audit outcome names must remain truthful. `clean_context_enqueued` or equivalent success evidence should only appear when a clean-context workflow actually ran and the notifier prompt was accepted after that workflow. Failed compaction or reset attempts should be distinct from mailbox completion and must not alter mailbox state.

Alternative considered: store diagnostics only in logs. Logs are useful, but notifier behavior is already audited in SQLite, and policy-driven recovery needs structured evidence in the same inspection path operators use for notifier status.

## Risks / Trade-offs

- [Risk] `/compact` may itself trigger the upstream failure being avoided. -> Mitigation: treat compaction as a preflight with structured failure diagnostics; default policy continues current-context delivery instead of clearing automatically.
- [Risk] Clear-context recovery loses valuable conversation state. -> Mitigation: keep `clear_context` opt-in and document it as a continuity trade-off.
- [Risk] Tool-specific labels leak into shared behavior. -> Mitigation: require tool-prefixed degraded error types and make `unknown` the only shared fallback.
- [Risk] Unsupported backends silently skip policy. -> Mitigation: reject unsupported `compact` policy with explicit status/support errors.
- [Risk] Notifier policy state expands the gateway SQLite schema. -> Mitigation: add forward-compatible defaults so existing notifier records behave as `continue_current` and `none`.
- [Risk] A reset or compaction preflight can leave the TUI not prompt-ready. -> Mitigation: do not send the semantic notifier prompt unless the preflight/reset workflow returns to prompt-ready posture.

## Migration Plan

Existing notifier state should default to `context_error_policy=continue_current` and `pre_notification_context_action=none`. That preserves behavior for all current users and archived OpenSpec guarantees.

Gateway schema migration should add nullable or defaulted fields for the new notifier policy and audit metadata. Status builders should normalize missing persisted values to the defaults.

Rollback is direct: ignore the new policy fields and return notifier behavior to current-context delivery. Persisted policy fields can remain inert until the change is re-enabled.

## Open Questions

- Should pre-notification compaction support headless Codex later through a structured CLI operation, or should it stay TUI-only until Codex exposes a reliable headless compaction control?
- Should notifier status expose the last degraded diagnostic directly, or should that remain only in audit history plus TUI tracked state?
