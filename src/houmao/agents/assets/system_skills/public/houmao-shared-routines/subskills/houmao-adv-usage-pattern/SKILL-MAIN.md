---
name: houmao-adv-usage-pattern
description: Use when a supported Houmao multi-step composition is needed for self-notification, notifier-prompt-driven mail rounds, local-close pairwise edge loops, or forward relay loops.
license: MIT
skill_invocation_notation: >
  Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
  SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
  accepted only as legacy input when SKILL-MAIN.md is absent.
  Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
  `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
  `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
  subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
  by parent subcommand parent. Intermediate subcommands act as object generators.
  Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints.
---

# Houmao Advanced Usage Patterns

## Workflow

1. **Handle explicit help first** without selecting a pattern or executing a control surface.
2. **Validate the inherited actor frame** from `houmao-shared-routines` and preserve its actor and targets.
3. **Select one subcommand** from **Subcommands**; route direct one-step work to its owning shared child instead.
4. **Load only the selected command page** and the direct-operation child guidance it names.
5. **Execute one bounded composition** and preserve its mailbox, gateway, notifier, and stop contracts.
6. **Return the result** with the selected pattern, targets, evidence, blockers, and explicit stop point.

If the user's task does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from the supported patterns, actor frame, direct-operation boundaries, and user request, then execute the plan.

## Actor Frame Gate

This parent-scoped routine loads only through `houmao-shared-routines`. Require the immutable admin or verified-agent frame validated by that parent. Admin routes keep explicit targets; agent routes use freshly verified self only where the selected pattern is self-scoped and require explicit peers otherwise. Missing or mismatched frames fail closed.

Use this Houmao skill when the task is a supported multi-step Houmao workflow composition rather than one direct mailbox, gateway, or lifecycle action.

This skill is intentionally above the direct-operation skills and below the maintained generated-loop skills. Keep exact mailbox actions in `houmao-shared-routines->houmao-agent-email-comms`, gateway and notifier control in `houmao-shared-routines->houmao-agent-gateway`, one notifier-driven open-mail round in `houmao-shared-routines->houmao-process-emails-via-gateway`, topology-rich generated execplans in `houmao-agent-loop-pro`, and lightweight Markdown/direct-SQL generated loops in `houmao-agent-loop-lite`.

## Help

When the user asks `$houmao-shared-routines adv-usage-pattern help`, `help for houmao-adv-usage-pattern`, `usage for houmao-adv-usage-pattern`, `available functionality for houmao-adv-usage-pattern`, or what this skill can do, answer from this section before choosing a pattern or reference page. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me design a notifier-driven mail loop", route to the matching workflow instead of stopping at generic help.

Purpose: explain supported multi-step Houmao workflow compositions that combine direct mailbox, gateway, notifier, and loop skills.

Available functionality:

- Self-notification choices between gateway reminders and self-mail backlog.
- Notifier-prompt-driven mail loops with on-event and optional on-tick behavior.
- One-round local-close driver-worker edge loops.
- Ordered relay loops that return final results to the origin.
- Guidance for choosing between elemental patterns, `houmao-agent-loop-lite`, and `houmao-agent-loop-pro`.

Common starting prompts:

- `$houmao-shared-routines adv-usage-pattern help`
- `$houmao-shared-routines adv-usage-pattern self-notification`
- `$houmao-shared-routines adv-usage-pattern notifier-prompt-driven mail loop`
- `$houmao-shared-routines adv-usage-pattern local-close edge loop`

Related skills and boundaries:

- Use `houmao-shared-routines->houmao-agent-email-comms` for one exact mailbox action.
- Use `houmao-shared-routines->houmao-agent-gateway` for gateway lifecycle, reminders, and mail-notifier control.
- Use `houmao-shared-routines->houmao-process-emails-via-gateway` for one notifier-reported open-mail round.
- Use `houmao-agent-loop-lite` or `houmao-agent-loop-pro` for generated loop packages.

## Subcommands

- Read [commands/self-notification.md](commands/self-notification.md) when a managed agent wants to notify itself about later work and needs to choose between live gateway reminders and self-mail backlog.
- Read [commands/notifier-prompt-driven-mail-loop.md](commands/notifier-prompt-driven-mail-loop.md) when mailbox notifications are the runtime driver: gateway mail-notifier prompts the target agent, generated or loop-specific on-event behavior handles mail, optional on-tick behavior runs once, and the agent must end the chat turn.
- Read [commands/pairwise-edge-loop-via-gateway-and-mailbox.md](commands/pairwise-edge-loop-via-gateway-and-mailbox.md) when one driver sends one request to one worker for one local-close edge-loop round and that same worker must return the final result to that same driver.
- Read [commands/relay-loop-via-gateway-and-mailbox.md](commands/relay-loop-via-gateway-and-mailbox.md) when one master or loop origin starts one ordered N-node relay lane, work moves forward along that lane, and the designated loop egress returns the final result to the origin through mailbox email.

## Multi-Agent Loop Chooser

- Prefer the local-close edge-loop pattern when exactly one driver sends one worker request for one local-close round and the final result should return to the same driver that sent that request.
- Prefer the forward relay-loop pattern when one master or loop origin starts one ordered relay lane, ownership should keep moving forward along that lane, and a later downstream loop egress should return the final result directly to that origin.
- Use the notifier-prompt-driven mail loop pattern for runtime wake-up posture, notifier appendix guidance, sender notify blocks, mail-event handling, and one-pass tick behavior inside a mailbox-driven loop.
- Use `houmao-agent-loop-lite` when the user explicitly wants a small generated-skill loop package with Markdown contracts, typed Markdown templates, and direct SQLite state.
- Use `houmao-agent-loop-pro` for composed topology, schema-rich generated execplans, rendered graphs, graph policy, multi-edge tree loops, multi-lane relay routes, or generated loop run-control actions. Choose `tree-loop` or `generic-loop` inside pro instead of routing to retired loop packages.

## Guardrails

- DO NOT treat this skill as a new control surface; it composes existing Houmao-owned skills.
- DO NOT replace the direct-operation skills when the task is only one send, list, notifier, or wakeup action.
- DO NOT claim durability beyond the mailbox open-work state and live gateway contracts the pattern page states explicitly.
- DO NOT ask managed agents to sleep, poll, tail logs, or wait in-chat for future mail or ticks.
