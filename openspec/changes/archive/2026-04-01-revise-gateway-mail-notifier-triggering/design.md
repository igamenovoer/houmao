## Context

The current gateway notifier mixes two independent ideas:

- reminder eligibility based on unread mail existing, and
- reminder suppression based on whether the same unread snapshot was already reminded once.

That model is currently implemented with a coarse readiness gate for local interactive sessions. The local tmux-backed adapter treats live tmux connectivity as prompt-admission readiness, while direct prompt control already has a stronger notion of readiness based on live TUI posture, accepting-input state, parsed-surface idleness, and stability. As a result, the notifier can enqueue another reminder while the provider UI is still busy, and once it records a digest for an unchanged unread snapshot it can suppress later reminders even when earlier reminders were interrupted or abandoned by operator work.

The desired behavior is simpler: unread mail remains eligible for reminder delivery until it becomes read or otherwise leaves the unread set. The only blocking factor is whether the managed prompt surface is truly ready to accept a new prompt now.

## Goals / Non-Goals

**Goals:**

- Gate notifier reminder enqueueing on the strongest live prompt-readiness signal available for the attached backend.
- Require local interactive/TUI-backed sessions to satisfy the same idle-and-ready-for-input posture that direct gateway prompt control already requires.
- Keep unread mail eligible for later reminders whenever unread mail still exists and the session becomes prompt-ready again, even if the unread snapshot is unchanged.
- Preserve the current reminder prompt shape that summarizes the current unread snapshot and lets the agent choose which message or messages to inspect and handle.
- Keep notifier bookkeeping separate from mailbox read state and avoid introducing notifier-owned “done” or “in-flight reminder resolved” state.

**Non-Goals:**

- Changing mailbox read/unread truth or transport semantics.
- Introducing one reminder prompt per unread message.
- Adding new notifier control routes or a second notifier state machine.
- Designing a new operator acknowledgement workflow for suppressing reminders manually.

## Decisions

### Decision: Notifier eligibility becomes readiness-gated level triggering

The notifier will treat unread mail as level-triggered work. If unread mail exists, that work remains eligible for reminder delivery until the unread set changes to remove it. Prior reminder delivery is not itself a suppression condition.

Why:

- This matches the operator expectation that interrupted or abandoned reminder turns should not retire unread mailbox work.
- It removes ambiguity around notifier-owned “done/undone” semantics.
- It keeps the model simple: unread truth comes from the mailbox, readiness truth comes from the live prompt surface.

Alternative considered:

- Keep unread-set deduplication but add a timeout or retry window. Rejected because it still invents notifier-owned suppression state and still fails the interruption case when an operator runs unrelated commands for an arbitrarily long period.

### Decision: Reuse prompt-ready posture instead of coarse gateway idleness

Notifier enqueueing will use the strongest existing prompt-ready signal available for the backend instead of treating connectivity plus empty queue as sufficient readiness.

For local interactive or other TUI-backed sessions, readiness should align with the live TUI prompt-control posture: idle turn state, accepting input, not editing input, ready posture, and stable parsed-surface idleness. For server-managed headless flows, the notifier can continue using the backend-owned “can accept prompt now” style control posture already exposed through the managed interface.

Why:

- The direct prompt-control path already codifies a stricter and more accurate notion of readiness than the current notifier path.
- Using the same readiness boundary reduces split-brain behavior between operator-initiated prompts and notifier-initiated prompts.

Alternative considered:

- Continue using `request_admission`, `active_execution`, and `queue_depth` alone. Rejected because those fields only describe gateway-managed work, not whether the provider UI is actually ready for another prompt.

### Decision: Preserve aggregated unread-snapshot prompts

The notifier will continue to summarize the full unread snapshot in one prompt and let the agent choose which message or messages to inspect and handle. Repeated reminders for unchanged unread mail will preserve that same snapshot-oriented prompt shape rather than creating per-message reminder state.

Why:

- The current prompt contract already matches the intended mailbox triage workflow.
- The bug is in reminder timing and suppression, not in snapshot summarization.

Alternative considered:

- Introduce one dedicated reminder per unread message. Rejected because it adds queue pressure and complicates agent behavior without solving the readiness or interruption problems.

### Decision: Keep notifier bookkeeping observational, not suppressive

Notifier persistence may continue to record operational data such as enabled state, poll interval, last poll time, last notification time, and per-poll audit evidence. It will not rely on persisted unread-set deduplication state to decide whether unread mail is still eligible for another reminder.

Why:

- Mailbox read state remains authoritative in the mailbox transport.
- Reminder suppression state would reintroduce the same conceptual bug under a different name.

Alternative considered:

- Track a reminder lifecycle with explicit “sent”, “acknowledged”, or “resolved” states. Rejected because the user requirement is that notifier logic remain simple and blocked only by live prompt readiness.

## Risks / Trade-offs

- [Repeated reminders may become noisy while unread mail persists] → Mitigation: gate strictly on live prompt readiness, preserve one aggregated snapshot prompt, and keep gateway log rate limiting plus audit history for observability.
- [Backend readiness signals are not identical across execution adapters] → Mitigation: define notifier eligibility in terms of the strongest backend-owned prompt-ready signal available, and cover local interactive plus managed headless paths explicitly in tests.
- [Existing persisted dedup fields or tests may imply the old model] → Mitigation: revise specs and tests together and treat any retained stored fields as inert compatibility baggage rather than behavioral state.

## Migration Plan

1. Revise the notifier specs to replace unread-set dedup suppression with readiness-gated repeated reminders.
2. Update gateway notifier tests to assert repeated eligibility for unchanged unread mail after prompt-ready posture returns.
3. Update implementation to reuse strong prompt-readiness checks and to stop treating stored unread-digest suppression as a blocker.
4. Update demo or operator-facing docs that currently describe unread-set dedup as intended behavior.

No external API migration is required because the control routes stay the same. Existing gateway-owned notifier persistence may remain on disk, but fields used only for unread-set suppression should no longer affect behavior.

## Open Questions

None at proposal time. The behavioral contract is intentionally narrowed to one rule: unread mail remains eligible until the prompt surface is ready and the agent has not marked that mail read.
