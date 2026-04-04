## Why

The current gateway mail notifier prompt mixes two jobs awkwardly: it gives a low-level gateway-operation tutorial and only later summarizes unread mail. That makes the wake-up prompt less useful for round-oriented mailbox work, and it does not provide a dedicated Houmao workflow skill for deciding which notified emails to process now versus later.

## What Changes

- Revise the gateway mail notifier prompt so the first section is a complete unread-email summary list for the current snapshot, covering all unread messages and only non-body metadata such as sender identity, subject, message references, and creation time.
- Revise that first section to instruct the agent to use a new Houmao-owned workflow skill named `houmao-process-emails-via-gateway` for the current notification round.
- Revise the later gateway-operations section so it emphasizes the exact live gateway URL for the current turn and lists the full shared mailbox endpoint URLs generated from that base URL.
- Add a projected runtime-owned mailbox skill `skills/mailbox/houmao-process-emails-via-gateway/` that teaches the round-oriented workflow for metadata-first triage, task-relevant message selection, message inspection, work execution, and post-success mark-read behavior.
- Clarify that after the agent finishes one processing round, it stops and waits for the next notifier wake-up instead of proactively polling for more mail.
- **BREAKING** Replace the current notifier prompt contract that explicitly centers `houmao-email-via-agent-gateway` and generic curl examples with a two-part contract centered on unread email summaries plus the new round-oriented processing skill.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-gateway-mail-notifier`: change the wake-up prompt contract to lead with all unread email summaries, trigger `houmao-process-emails-via-gateway`, and present dynamic full gateway endpoint URLs in a later operations section.
- `agent-mailbox-system-skills`: add the projected `houmao-process-emails-via-gateway` runtime-owned skill and define its relationship to the lower-level `houmao-email-via-agent-gateway` protocol skill.

## Impact

- Affected code: notifier prompt rendering and unread-summary formatting under `src/houmao/agents/realm_controller/gateway_service.py`, plus runtime-owned mailbox skill projection assets under `src/houmao/agents/realm_controller/assets/system_skills/mailbox/`.
- Affected prompt assets: `src/houmao/agents/realm_controller/assets/system_prompts/mailbox/mail-notifier.md`.
- Affected skills/docs: mailbox system skill documentation, especially `houmao-email-via-agent-gateway`, transport-specific mailbox skills, and the new `houmao-process-emails-via-gateway` skill.
- Affected tests: notifier prompt rendering assertions, mailbox skill projection expectations, and demo or gateway tests that currently assert the old prompt wording or old skill reference.
