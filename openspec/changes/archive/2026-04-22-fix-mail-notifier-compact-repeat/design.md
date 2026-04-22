## Context

Gateway mail-notifier now supports `pre_notification_context_action=compact` for supported Codex TUI targets. The current poll loop computes the eligible mail snapshot, checks readiness, optionally runs `/compact`, and then enqueues an internal `mail_notifier_prompt`.

That structure has two gaps for the reported bug:

1. The notifier has no durable notion of "this currently eligible mail already triggered compaction," so unchanged eligible mail can cause `/compact` again on later cycles.
2. The current implementation keeps compaction bookkeeping separate from mailbox read state, but it does not yet separate compaction bookkeeping from repeated wake-up behavior. Existing product behavior intentionally allows repeated notifier prompts for unchanged eligible mail; the bug is that repeated prompts can also imply repeated compaction.

The requested product rule is narrower and sharper than prompt dedup: one eligible mail item should trigger at most one pre-notification compaction while it remains eligible for the configured notifier mode.

## Goals / Non-Goals

**Goals:**
- Enforce one-shot compaction for each continuously eligible mail item.
- Preserve existing mode-based eligibility rules for `any_inbox` and `unread_only`.
- Preserve current prompt repeat behavior unless mailbox state or future product decisions change it separately.
- Keep compaction bookkeeping separate from notification timing, mailbox read state, and prompt dedup bookkeeping.
- Update reference docs and regression coverage so the contract is explicit.

**Non-Goals:**
- Suppress repeated notifier prompts for unchanged eligible mail.
- Change mailbox completion semantics or archive behavior.
- Introduce new public CLI or HTTP options.
- Redesign degraded-context recovery beyond the compaction bug fix.

## Decisions

### Decision: Persist compaction history as eligible-message identity, not as prompt digest

The notifier will persist runtime-owned compaction bookkeeping keyed by eligible `message_ref` values rather than trying to reuse `last_notified_digest`.

On each poll cycle:
- compute the current eligible message-ref set for the configured mode,
- prune remembered compacted refs to the current eligible set,
- run compaction only when at least one currently eligible ref has not yet been compacted during its current eligibility stretch,
- after successful compaction, mark the whole current eligible set as compacted.

This matches the product rule directly: a given mail item triggers at most one compaction while it remains eligible.

Alternatives considered:
- Reuse `last_notified_digest`: rejected because digest-level tracking cannot express "mail A already compacted, mail B newly eligible" without conflating compaction control with prompt dedup.
- Use in-memory-only bookkeeping: rejected because a gateway restart would forget compaction history for still-eligible mail and could re-trigger `/compact` for the same work.

### Decision: Treat compaction bookkeeping as independent from notifier prompt repetition

The fix will not change current repeated wake-up semantics for unchanged eligible mail. Repeated `mail_notifier_prompt` enqueueing may still happen on later cycles when mail remains eligible and prompt-readiness gates reopen, but those later cycles will not re-run compaction for previously remembered eligible mail.

This keeps the change tightly scoped to the bug and avoids reintroducing dormant `dedup_skip` semantics as part of the compaction fix.

Alternatives considered:
- Enable full digest-based prompt dedup at the same time: rejected because it changes broader notifier semantics and conflicts with current docs/tests that allow repeated wake-ups for unchanged eligible mail.

### Decision: Forget compaction history when mail leaves the eligible set

Compaction history will be retained only for the currently eligible set. When mail becomes ineligible, the remembered compaction marker for that message will be dropped automatically on the next cycle.

This supports both notifier modes:
- in `any_inbox`, archive/move/removal ends the eligibility stretch,
- in `unread_only`, becoming read or archived ends the eligibility stretch.

If a previously ineligible message later becomes eligible again, that starts a new eligibility stretch and may trigger one new compaction.

Alternatives considered:
- Keep permanent "already compacted once ever" history: rejected because it would make later legitimate re-eligibility unable to request a fresh compaction.

### Decision: Let queued notifier prompts participate in TUI prompt-submission tracking

For TUI-backed dispatch, queued `mail_notifier_prompt` work should arm the same prompt-submission tracking path used by ordinary queued prompt requests.

This is a hardening measure rather than the primary product contract. It reduces the chance that the gateway immediately considers the surface prompt-ready again before the queued notifier prompt is reflected in tracking state.

Alternatives considered:
- Rely only on queue depth and active execution snapshots: rejected because the tracker is already the source of truth for TUI prompt-readiness and can otherwise lag behind internal notifier dispatch.

## Risks / Trade-offs

- Persisted compaction bookkeeping adds notifier-state schema surface -> mitigate by keeping it runtime-owned, bounded to the current eligible set, and absent from public API unless later needed.
- Successful compaction followed by failed prompt enqueue or later busy cycles will still count as "already compacted" for that eligibility stretch -> acceptable because the product rule constrains compaction count, not wake-up count.
- Transport-specific `message_ref` stability becomes part of compaction identity -> mitigate by reusing the same `message_ref` identity already used for notifier audit summaries and digest computation.
- Adding tracking hardening alongside the state fix increases implementation touch points -> mitigate by keeping the behavior-level spec focused on compaction semantics and treating TUI tracking participation as an internal design choice with targeted regression coverage.

## Migration Plan

1. Extend gateway notifier runtime storage with one persisted representation of the currently remembered compacted eligible message refs.
2. Add a storage migration that defaults existing runtimes to an empty remembered set.
3. Update the notifier cycle to prune remembered refs to the current eligible set and gate compaction on newly eligible refs only.
4. Update queued notifier-prompt dispatch so TUI tracking records internal notifier prompt submission.
5. Refresh gateway mail-notifier reference docs and add regression tests for repeated unchanged mail and newly expanded eligible sets.

Rollback is straightforward: code can ignore the new runtime-owned bookkeeping field, and the extra persisted column/data can remain inert.

## Open Questions

None currently. The main product decision for this change is already settled: compaction is one-shot per continuous eligible-mail stretch, while repeated wake-up prompts remain out of scope.
