## Why

Houmao's advanced usage guidance currently covers self-notification, but it does not describe a robust multi-agent relay loop where one agent hands work to another agent, waits for downstream confirmation, and eventually receives a final email result back from a designated loop exit. That gap matters now because the current system already has the needed primitives, but without an endorsed pattern agents can easily choose unsafe waiting or retry behavior under ordinary network instability.

## What Changes

- Add a supported advanced-usage pattern for multi-agent relay loops driven by queued gateway prompts plus mailbox receipts and final-result mail.
- Define the relay-loop roles and message flow: loop origin, loop ingress, relay agents, loop egress, receipt mail, final result mail, and final result acknowledgement.
- Specify that each sender persists local loop state, sends the downstream handoff, arms a wakeup mechanism for follow-up, and ends the current turn instead of actively waiting inside one long LLM round.
- Specify explicit workflow identifiers such as `loop_id`, `handoff_id`, and result acknowledgement state so repeated sends can be deduplicated safely.
- Specify that the mutable relay-loop ledger lives under `HOUMAO_JOB_DIR` as per-session scratch bookkeeping, not under `HOUMAO_MEMORY_DIR`.
- Specify how agents obtain timing thresholds: derive them from task context or user-provided deadlines when available, and ask the user when a materially important value cannot be chosen sensibly from context.
- Define the recommended single-agent supervisor model for many outbound loops: one local ledger, one supervisor reminder, and optional durable self-mail checkpoint instead of one live reminder per active loop.
- Include concrete text-block templates for downstream handoff requests, mailbox follow-up messages, and reminder text so the pattern shows agents exactly what information must be recorded.
- Clarify when the hybrid `reminder + optional self-mail checkpoint` approach is preferred over pure reminder-only or pure self-mail-only coordination.
- Resync the gateway mail-notifier reference page with current source behavior so it no longer claims digest-based suppression that the implementation does not currently perform.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-adv-usage-pattern-skill`: extend the packaged advanced-usage skill with a supported multi-agent relay-loop pattern that composes queued gateway prompts, mailbox receipts/results, supervisor reminders, and optional self-mail checkpoints.
- `docs-gateway-mail-notifier-reference`: update the mail-notifier reference requirements so the page documents the current source-truth polling and repeat-notification behavior accurately.

## Impact

- Affected spec: `openspec/specs/houmao-adv-usage-pattern-skill/spec.md`
- Affected spec: `openspec/specs/docs-gateway-mail-notifier-reference/spec.md`
- Affected skill assets: `src/houmao/agents/assets/system_skills/houmao-adv-usage-pattern/SKILL.md` and new pattern pages under `src/houmao/agents/assets/system_skills/houmao-adv-usage-pattern/patterns/`
- Affected docs: `docs/reference/gateway/operations/mail-notifier.md`
- Affected validation surface: system-skill packaging and asset tests that assert projected Houmao skill contents
- No new gateway, mailbox, or manager API surface; this change documents a supported composition over existing surfaces
