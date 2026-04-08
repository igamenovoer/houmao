---
name: houmao-adv-usage-pattern
description: Use Houmao's advanced-usage pattern skill for supported multi-step workflow compositions such as unified self-notification via gateway reminders or self-mail.
license: MIT
---

# Houmao Advanced Usage Patterns

Use this Houmao skill when the task is a supported multi-step Houmao workflow composition rather than one direct mailbox, gateway, or lifecycle action.

This skill is intentionally above the direct-operation skills. Keep exact mailbox actions in `houmao-agent-email-comms`, gateway and notifier control in `houmao-agent-gateway`, and one notifier-driven unread-mail round in `houmao-process-emails-via-gateway`.

## Supported Patterns

- Read [patterns/self-notification.md](patterns/self-notification.md) when a managed agent wants to notify itself about later work and needs to choose between live gateway reminders and self-mail backlog.

## Guardrails

- Do not treat this skill as a new control surface; it composes existing Houmao-owned skills.
- Do not replace the direct-operation skills when the task is only one send, check, notifier, or wakeup action.
- Do not claim durability beyond the mailbox unread state and live gateway contracts the pattern page states explicitly.
