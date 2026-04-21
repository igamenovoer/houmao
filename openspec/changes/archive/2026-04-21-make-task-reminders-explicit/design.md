## Context

Issue 27 points at a prompt-quality problem rather than a gateway-reminder feature gap. Houmao already keeps `task-reminder` default-disabled, and richer self-notification behavior already lives in explicit advanced-usage patterns. The problematic seam is the managed prompt-header text itself: when `task-reminder` is enabled, the contract currently tells agents to create a live reminder for generic "potentially long-running work" and prescribes a short default delay.

That wording makes reminder creation feel habitual instead of intentional. It also conflates two different cases:

- useful reminder use, where a reminder guards a concrete finalization or supervision obligation,
- low-value reminder use, where the reminder just causes the agent to re-orient later without adding new operational value.

The change should narrow the prompt contract without changing the surrounding launch/profile policy model, gateway reminder API, or optional advanced self-notification patterns.

## Goals / Non-Goals

**Goals:**

- Keep `task-reminder` default-disabled and preserve existing section controls.
- Rewrite the `task-reminder` contract so it only authorizes reminder creation for explicit self-reminding requests or concrete supervision/finalization checks.
- Remove the fixed short default delay from the managed prompt-header contract.
- Direct agents toward local todo or working state when no concrete reminder target exists.
- Bring the dedicated reference page into alignment with the new prompt contract.

**Non-Goals:**

- Changing the gateway reminder transport, ranking model, or reminder durability semantics.
- Reworking optional advanced self-notification patterns such as self-mail versus live reminder selection.
- Changing reply-hardening behavior in `houmao-process-emails-via-gateway` as part of this change.
- Renaming `task-reminder` or changing CLI/profile section names in v1.

## Decisions

### 1. Fix the contract at the managed prompt-header seam

The change should update the managed `task-reminder` section text and its normative spec, rather than introducing new runtime gating or policy flags.

Rationale:

- The issue is about what the agent is being told to do.
- `task-reminder` is already opt-in, so narrowing the instruction fixes the bad posture without expanding the operator surface.
- A prompt-contract change is simpler and lower-risk than adding new launch-time controls.

Alternatives considered:

- Add a second reminder mode or a new managed-header section. Rejected because the current problem is incorrect guidance, not missing operator knobs.
- Remove `task-reminder` entirely. Rejected because reminder hardening still has valid use cases when explicitly requested or tied to concrete supervision.

### 2. Make reminder eligibility concrete instead of duration-based

The new contract should authorize reminders only when one of two conditions is true:

- the operator explicitly asked for a later self-reminder or wake-up behavior, or
- the task has a concrete supervision/finalization obligation that the reminder is guarding.

Concrete examples should include required replies, required output files, stalled-agent or stalled-loop checks, and similar operator-valuable verification work.

Rationale:

- "Potentially long-running work" is too broad and naturally produces ceremonial reminders.
- Concrete guarded obligations are easier for agents to evaluate and easier for operators to trust.

Alternatives considered:

- Keep the duration-based trigger but increase the interval. Rejected because a slower ceremonial reminder is still ceremonial.
- Restrict reminders only to mailbox work. Rejected because useful supervision reminders can also apply to non-mail tasks.

### 3. Remove the fixed default delay from the prompt contract

The managed header should stop prescribing a universal short delay such as 10 seconds.

Rationale:

- A hardcoded short delay creates accidental cost pressure and encourages generic check-back behavior.
- Different reminder cases have different useful windows, and some cases should use no reminder at all.
- Delay choice belongs to the concrete workflow or explicit operator request, not the generic prompt header.

Alternatives considered:

- Replace 10 seconds with a longer fixed delay. Rejected because the core problem is not only the number; it is the existence of a generic prescribed reminder cadence.

### 4. Explicitly bias no-reminder cases toward local working state

When the enabled section does not find a concrete reminder target, the prompt should direct the agent to keep using local todo or working state instead of creating a ceremonial reminder.

Rationale:

- The repository already treats local memo/todo state as the normal place for ongoing task context.
- This gives agents a positive alternative instead of only telling them what not to do.

## Risks / Trade-offs

- [Risk] Narrowing the prompt could reduce reminder usage in cases where a reminder would have been marginally helpful. → Mitigation: keep explicit operator-requested self-reminding and concrete supervision/finalization reminders in scope.
- [Risk] "Concrete supervision/finalization goal" could still be interpreted too loosely. → Mitigation: include representative examples and explicitly reject ceremonial self-pings in the contract and docs.
- [Risk] Optional advanced self-notification docs still recommend reminders in their own contexts. → Mitigation: keep this change scoped to the managed prompt header and its reference docs, where the problematic default posture lives.

## Migration Plan

This is a behavior-tightening change for an existing opt-in prompt section. No stored data or CLI migration is required.

Implementation rollout should:

1. Update the managed prompt-header text in `src/houmao/agents/managed_prompt_header.py`.
2. Update the reference docs in `docs/reference/run-phase/managed-prompt-header.md`.
3. Add or refresh prompt-focused verification so the rendered `task-reminder` text no longer mentions generic long-running work or a fixed 10-second delay.

Rollback is straightforward: restore the previous prompt text and documentation if operators report that the narrower contract blocks necessary reminder flows.

## Open Questions

- Should a later follow-up also narrow the advanced self-notification pattern's "prefer reminders when unsure" wording, or is the managed prompt header the only posture seam that needs fixing right now?
- Should a future change introduce named reminder intents such as reply-hardening versus supervision-check, or is clarified prompt wording enough?
