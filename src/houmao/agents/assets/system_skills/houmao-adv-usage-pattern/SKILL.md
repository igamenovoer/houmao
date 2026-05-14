---
name: houmao-adv-usage-pattern
description: Use Houmao's advanced-usage pattern skill for supported multi-step workflow compositions such as self-notification, notifier-prompt-driven mail loops, local-close edge loops, and forward relay loops built from existing Houmao skills.
license: MIT
---

# Houmao Advanced Usage Patterns

Use this Houmao skill when the task is a supported multi-step Houmao workflow composition rather than one direct mailbox, gateway, or lifecycle action.

This skill is intentionally above the direct-operation skills and below the maintained generated-loop skills. Keep exact mailbox actions in `houmao-agent-email-comms`, gateway and notifier control in `houmao-agent-gateway`, one notifier-driven open-mail round in `houmao-process-emails-via-gateway`, topology-rich generated execplans in `houmao-agent-loop-pro`, and lightweight Markdown/direct-SQL generated loops in `houmao-agent-loop-lite`.

## Help

When the user asks `$houmao-adv-usage-pattern help`, `help for houmao-adv-usage-pattern`, `usage for houmao-adv-usage-pattern`, `available functionality for houmao-adv-usage-pattern`, or what this skill can do, answer from this section before choosing a pattern or reference page. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me design a notifier-driven mail loop", route to the matching workflow instead of stopping at generic help.

Purpose: explain supported multi-step Houmao workflow compositions that combine direct mailbox, gateway, notifier, and loop skills.

Available functionality:

- Self-notification choices between gateway reminders and self-mail backlog.
- Notifier-prompt-driven mail loops with on-event and optional on-tick behavior.
- One-round local-close driver-worker edge loops.
- Ordered relay loops that return final results to the origin.
- Guidance for choosing between elemental patterns, `houmao-agent-loop-lite`, and `houmao-agent-loop-pro`.

Common starting prompts:

- `$houmao-adv-usage-pattern help`
- `$houmao-adv-usage-pattern self-notification`
- `$houmao-adv-usage-pattern notifier-prompt-driven mail loop`
- `$houmao-adv-usage-pattern local-close edge loop`

Related skills and boundaries:

- Use `houmao-agent-email-comms` for one exact mailbox action.
- Use `houmao-agent-gateway` for gateway lifecycle, reminders, and mail-notifier control.
- Use `houmao-process-emails-via-gateway` for one notifier-reported open-mail round.
- Use `houmao-agent-loop-lite` or `houmao-agent-loop-pro` for generated loop packages.

## Supported Patterns

- Read [patterns/self-notification.md](patterns/self-notification.md) when a managed agent wants to notify itself about later work and needs to choose between live gateway reminders and self-mail backlog.
- Read [patterns/notifier-prompt-driven-mail-loop.md](patterns/notifier-prompt-driven-mail-loop.md) when mailbox notifications are the runtime driver: gateway mail-notifier prompts the target agent, generated or loop-specific on-event behavior handles mail, optional on-tick behavior runs once, and the agent must end the chat turn.
- Read [patterns/pairwise-edge-loop-via-gateway-and-mailbox.md](patterns/pairwise-edge-loop-via-gateway-and-mailbox.md) when one driver sends one request to one worker for one local-close edge-loop round and that same worker must return the final result to that same driver.
- Read [patterns/relay-loop-via-gateway-and-mailbox.md](patterns/relay-loop-via-gateway-and-mailbox.md) when one master or loop origin starts one ordered N-node relay lane, work moves forward along that lane, and the designated loop egress returns the final result to the origin through mailbox email.

## Multi-Agent Loop Chooser

- Prefer the local-close edge-loop pattern when exactly one driver sends one worker request for one local-close round and the final result should return to the same driver that sent that request.
- Prefer the forward relay-loop pattern when one master or loop origin starts one ordered relay lane, ownership should keep moving forward along that lane, and a later downstream loop egress should return the final result directly to that origin.
- Use the notifier-prompt-driven mail loop pattern for runtime wake-up posture, notifier appendix guidance, sender notify blocks, mail-event handling, and one-pass tick behavior inside a mailbox-driven loop.
- Use `houmao-agent-loop-lite` when the user explicitly wants a small generated-skill loop package with Markdown contracts, typed Markdown templates, and direct SQLite state.
- Use `houmao-agent-loop-pro` for composed topology, schema-rich generated execplans, rendered graphs, graph policy, multi-edge tree loops, multi-lane relay routes, or generated loop run-control actions. Choose `tree-loop` or `generic-loop` inside pro instead of routing to retired loop packages.

## Guardrails

- Do not treat this skill as a new control surface; it composes existing Houmao-owned skills.
- Do not replace the direct-operation skills when the task is only one send, list, notifier, or wakeup action.
- Do not claim durability beyond the mailbox open-work state and live gateway contracts the pattern page states explicitly.
- Do not ask managed agents to sleep, poll, tail logs, or wait in-chat for future mail or ticks.
