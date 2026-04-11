---
name: houmao-adv-usage-pattern
description: Use Houmao's advanced-usage pattern skill for supported multi-step workflow compositions such as self-notification, pairwise edge loops, and forward relay loops built from existing Houmao skills.
license: MIT
---

# Houmao Advanced Usage Patterns

Use this Houmao skill when the task is a supported multi-step Houmao workflow composition rather than one direct mailbox, gateway, or lifecycle action.

This skill is intentionally above the direct-operation skills and below the dedicated loop-planning skills. Keep exact mailbox actions in `houmao-agent-email-comms`, gateway and notifier control in `houmao-agent-gateway`, one notifier-driven unread-mail round in `houmao-process-emails-via-gateway`, and graph/run planning in the dedicated loop skills.

## Supported Patterns

- Read [patterns/self-notification.md](patterns/self-notification.md) when a managed agent wants to notify itself about later work and needs to choose between live gateway reminders and self-mail backlog.
- Read [patterns/pairwise-edge-loop-via-gateway-and-mailbox.md](patterns/pairwise-edge-loop-via-gateway-and-mailbox.md) when one driver sends one request to one worker for one elemental edge-loop round and that same worker must return the final result to that same driver.
- Read [patterns/relay-loop-via-gateway-and-mailbox.md](patterns/relay-loop-via-gateway-and-mailbox.md) when one master or loop origin starts one ordered N-node relay lane, work moves forward along that lane, and the designated loop egress returns the final result to the origin through mailbox email.

## Multi-Agent Loop Chooser

- Prefer the pairwise edge-loop pattern when exactly one driver sends one worker request for one local-close round and the final result should return to the same driver that sent that request.
- Prefer the forward relay-loop pattern when one master or loop origin starts one ordered relay lane, ownership should keep moving forward along that lane, and a later downstream loop egress should return the final result directly to that origin.
- Use `houmao-agent-loop-generic` for composed topology, mixed pairwise/relay graph planning, rendered graphs, graph policy, multi-edge pairwise runs, multi-lane relay routes, or `start`/`status`/`stop` run-control actions. Use the selected pairwise loop-planning skill only when it is explicitly invoked or already selected for a pairwise-only run.

## Guardrails

- Do not treat this skill as a new control surface; it composes existing Houmao-owned skills.
- Do not replace the direct-operation skills when the task is only one send, check, notifier, or wakeup action.
- Do not claim durability beyond the mailbox unread state and live gateway contracts the pattern page states explicitly.
