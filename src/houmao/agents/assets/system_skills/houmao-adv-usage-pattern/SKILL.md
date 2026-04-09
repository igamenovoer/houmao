---
name: houmao-adv-usage-pattern
description: Use Houmao's advanced-usage pattern skill for supported multi-step workflow compositions such as self-notification, pairwise edge loops, and forward relay loops built from existing Houmao skills.
license: MIT
---

# Houmao Advanced Usage Patterns

Use this Houmao skill when the task is a supported multi-step Houmao workflow composition rather than one direct mailbox, gateway, or lifecycle action.

This skill is intentionally above the direct-operation skills. Keep exact mailbox actions in `houmao-agent-email-comms`, gateway and notifier control in `houmao-agent-gateway`, and one notifier-driven unread-mail round in `houmao-process-emails-via-gateway`.

## Supported Patterns

- Read [patterns/self-notification.md](patterns/self-notification.md) when a managed agent wants to notify itself about later work and needs to choose between live gateway reminders and self-mail backlog.
- Read [patterns/pairwise-edge-loop-via-gateway-and-mailbox.md](patterns/pairwise-edge-loop-via-gateway-and-mailbox.md) when one driver sends work to one worker and that same worker must close the loop locally by returning the final result to that same driver.
- Read [patterns/relay-loop-via-gateway-and-mailbox.md](patterns/relay-loop-via-gateway-and-mailbox.md) when a managed agent needs a robust multi-agent relay loop where work enters at one live-gateway agent, may transit across additional live-gateway agents, and the designated loop exit returns the final result to the origin through mailbox email.

## Multi-Agent Loop Chooser

- Prefer the pairwise edge-loop pattern when each delegation edge should close locally, the intermediate agent must integrate child results before replying upstream, or the final result for one loop round should always return to the same agent that sent that round's request.
- Prefer the forward relay-loop pattern when ownership should keep moving forward across agents and a later downstream loop egress should return the final result directly to a more distant origin.

## Guardrails

- Do not treat this skill as a new control surface; it composes existing Houmao-owned skills.
- Do not replace the direct-operation skills when the task is only one send, check, notifier, or wakeup action.
- Do not claim durability beyond the mailbox unread state and live gateway contracts the pattern page states explicitly.
