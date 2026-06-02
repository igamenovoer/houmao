---
name: houmao-mailbox-mgr
description: Use Houmao's mailbox-administration skill for filesystem mailbox roots, project mailbox roots, and late local managed-agent mailbox binding.
license: MIT
---

# Houmao Mailbox Manager

Use this Houmao skill when the task is mailbox administration rather than ordinary mailbox participation. This is the packaged Houmao-owned entrypoint for creating, validating, repairing, cleaning, exporting, or inspecting filesystem mailbox roots and for late filesystem mailbox binding on existing local managed agents.

The trigger word `houmao` is intentional. Use the `houmao-mailbox-mgr` skill name directly when you intend to activate this Houmao-owned skill.

## Help

When the user asks `$houmao-mailbox-mgr help`, `help for houmao-mailbox-mgr`, `usage for houmao-mailbox-mgr`, `available functionality for houmao-mailbox-mgr`, or what this skill can do, answer from this section before choosing a mailbox-admin lane, action page, command, reference, or missing-input question. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me register a mailbox account", route to the matching workflow instead of stopping at generic help.

Purpose: administer Houmao mailbox roots, registrations, structural projections, and late filesystem mailbox bindings.

Available functionality:

- Initialize, inspect, repair, clean, clear, and export filesystem or project mailbox roots.
- Register, inspect, unregister, and clean mailbox accounts.
- List, inspect, or clear structural message projections.
- Inspect, add, update, or remove late filesystem mailbox binding for an existing local managed agent.

Common starting prompts:

- `$houmao-mailbox-mgr help`
- `$houmao-mailbox-mgr project mailbox status`
- `$houmao-mailbox-mgr register <address>`
- `$houmao-mailbox-mgr agent binding status for <agent>`

Related skills and boundaries:

- Use `houmao-agent-email-comms` for ordinary mailbox send, reply, read, mark, move, or archive work.
- Use `houmao-agent-gateway` for gateway mail-notifier, reminders, or gateway-only state.
- Use `houmao-agent-definition` for same-root mailbox preparation that is part of specialist-backed easy launch.
- Treat Stalwart bootstrap and operation as outside the filesystem mailbox-admin command lane.

## Scope

This packaged skill covers exactly these maintained mailbox-administration surfaces:

- `help` (read-only meta operation)
- `houmao-mgr mailbox ...`
- `houmao-mgr project mailbox ...`
- `houmao-mgr agents single --agent-id <id> mailbox ...` or `--agent-name <name>`

This packaged skill does not cover:

- `houmao-mgr agents self mail ...` and `houmao-mgr agents single ... mail ...`
- shared `/v1/mail/*` workflow
- `houmao-mgr agents self gateway mail-notifier ...` and `houmao-mgr agents single ... gateway mail-notifier ...`
- direct gateway `/v1/mail-notifier` or `/v1/reminders`
- ad hoc filesystem editing inside mailbox roots

## Workflow

Before starting the workflow, answer explicit skill-help intent from `## Help` and stop.

1. Identify whether the user wants mailbox-root lifecycle, manual mailbox-account lifecycle, structural mailbox inspection, or late mailbox binding for one existing managed agent.
2. Select the maintained lane:
   - arbitrary filesystem mailbox root -> `houmao-mgr mailbox ...`
   - project overlay mailbox root -> `houmao-mgr project mailbox ...`
   - existing local managed-agent late binding -> `houmao-mgr agents single --agent-id <id> mailbox ...` or `--agent-name <name>`
3. Keep mailbox ownership boundaries explicit:
   - use `mailbox init|status|repair|cleanup|clear-messages|export` to manage the shared mailbox root itself
   - use `mailbox clear-messages` or `project mailbox clear-messages` when the operator wants to remove delivered emails while keeping mailbox accounts registered
   - use `mailbox messages clear --address` or `project mailbox messages clear --address` when the operator wants to remove delivered emails visible to one selected mailbox account while preserving other accounts
   - use `mailbox export` or `project mailbox export` when the operator wants to archive filesystem mailbox state; default export materializes symlinks so the archive can move to filesystems that do not support symlink artifacts
   - use `mailbox register|unregister` or `project mailbox register|unregister` for manual mailbox-account administration under that root
   - use `agents single ... mailbox ...` when the task is adding or changing mailbox support for an already-running local managed agent
   - when the user is preparing a new specialist-backed easy instance whose ordinary mailbox address will be derived from the managed-agent name under the same root, explain that mailbox registration may be owned by the later `project agents launch` step rather than by manual preregistration here
4. Recover omitted inputs from the current prompt first and recent chat context second, but only when the user stated them explicitly.
5. Keep mailbox identity guidance explicit when the user needs help choosing values:
   - ordinary principal ids use the canonical `HOUMAO-<agentname>` form
   - ordinary managed-agent mailbox addresses use `<agentname>@houmao.localhost`
   - mailbox local parts beginning with `HOUMAO-` under `houmao.localhost` are reserved for Houmao-owned system principals rather than ordinary managed-agent mailbox addresses
   - when the user has not specified a mailbox domain, recommend `houmao.localhost`
6. Choose one `houmao-mgr` launcher for the current turn:
   - first run `command -v houmao-mgr` and use the `houmao-mgr` already on `PATH` when present
   - if that lookup fails, use `uv tool run --from houmao houmao-mgr`
   - only if the PATH lookup and uv-managed fallback do not satisfy the turn, choose the appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`
   - if the user explicitly asks for a specific launcher, follow that request instead of the default order
7. Reuse that same chosen launcher for the selected mailbox-admin action.
8. For supported mailbox command authoring, build the direct maintained command before executing:
   - `mailbox <verb>` for arbitrary filesystem mailbox-root commands
   - `project mailbox <verb>` for active project mailbox-root commands
   - `mailbox accounts <verb>` and `project mailbox accounts <verb>` for account inspection
   - `mailbox messages <verb>` and `project mailbox messages <verb>` for structural message inspection or clearing
   - `agents single ... mailbox status|register|unregister` for late binding on an existing local managed agent
9. Include only fields the user explicitly supplied or that were recovered from explicit recent context.
10. If required input is missing or explicit inputs conflict, stop and recover the missing or conflicting input before running the target command.
11. Load exactly one action page for the task you need to complete.
12. Report the result from the command that ran and keep mailbox-admin routing boundaries explicit.

## Actions

- Read [actions/init.md](actions/init.md) to bootstrap or validate one arbitrary filesystem mailbox root or one project mailbox root.
- Read [actions/status.md](actions/status.md) to inspect mailbox-root health for one arbitrary filesystem mailbox root or one project mailbox root.
- Read [actions/register.md](actions/register.md) to register one filesystem mailbox account under one arbitrary mailbox root or one project mailbox root.
- Read [actions/unregister.md](actions/unregister.md) to deactivate or purge one filesystem mailbox account under one arbitrary mailbox root or one project mailbox root.
- Read [actions/repair.md](actions/repair.md) to rebuild filesystem mailbox root index state for one arbitrary mailbox root or one project mailbox root.
- Read [actions/cleanup.md](actions/cleanup.md) to clean inactive or stashed registrations under one arbitrary mailbox root or one project mailbox root.
- Read [actions/clear-messages.md](actions/clear-messages.md) to clear delivered mailbox messages while preserving registrations under one arbitrary mailbox root or one project mailbox root.
- Read [actions/export.md](actions/export.md) to archive all accounts or selected filesystem mailbox accounts under one arbitrary mailbox root or one project mailbox root.
- Read [actions/accounts-list.md](actions/accounts-list.md) to inspect mailbox registrations under one arbitrary mailbox root or one project mailbox root.
- Read [actions/accounts-get.md](actions/accounts-get.md) to inspect one mailbox registration under one arbitrary mailbox root or one project mailbox root.
- Read [actions/messages-list.md](actions/messages-list.md) to inspect structural message projections for one mailbox address under one arbitrary mailbox root or one project mailbox root.
- Read [actions/messages-get.md](actions/messages-get.md) to inspect one structurally projected message for one mailbox address under one arbitrary mailbox root or one project mailbox root.
- Read [actions/messages-clear.md](actions/messages-clear.md) to clear delivered mailbox messages visible to one selected mailbox address while preserving registrations and other accounts.
- Read [actions/agent-binding-status.md](actions/agent-binding-status.md) to inspect late filesystem mailbox posture for one existing local managed agent.
- Read [actions/agent-binding-register.md](actions/agent-binding-register.md) to add or update one late filesystem mailbox binding for one existing local managed agent.
- Read [actions/agent-binding-unregister.md](actions/agent-binding-unregister.md) to remove one late filesystem mailbox binding from one existing local managed agent.

## References

- Read [references/launcher-resolution.md](references/launcher-resolution.md) when launcher precedence for `houmao-mgr` matters.
- Read [references/root-selection.md](references/root-selection.md) when you need to choose between the arbitrary mailbox-root lane, the project mailbox lane, and the existing-agent late-binding lane.
- Read [references/mode-vocabulary.md](references/mode-vocabulary.md) when registration or deregistration mode semantics matter.
- Read [references/structural-vs-actor-state.md](references/structural-vs-actor-state.md) when the task involves mailbox message inspection versus actor-scoped unread or read state.
- Read [references/stalwart-boundary.md](references/stalwart-boundary.md) when Stalwart transport context appears in a mailbox-admin task.

## Missing Input Questions

- Recover required values from the current prompt first and recent chat context second, but only when the user stated them explicitly.
- If any required input is still missing after that check, ask the user for exactly the missing fields instead of guessing.
- When asking for missing input, use readable Markdown:
  - separate `Required` values from `Optional` modifiers
  - `Required`: values that block the selected mailbox command, such as lane, mailbox root, project target, managed-agent selector, mailbox address, principal id, message reference, export target, or action mode
  - `Optional`: launcher preference, mailbox domain default, cleanup/export mode, filters, symlink mode, purge mode, or skip choices; if none apply, say `Optional: none for this step.`
  - use a short bullet list when only one or two required fields are missing
  - use a compact table when the mailbox-admin lane or several required fields need clarification
- Name the command you intend to run and show only the missing fields needed for that command.
- Do not use this format for user-task or domain-intent questions unless the question is about Houmao runtime behavior.

## Routing Guidance

- Use `actions/init.md`, `actions/status.md`, `actions/register.md`, `actions/unregister.md`, `actions/repair.md`, `actions/cleanup.md`, `actions/clear-messages.md`, `actions/export.md`, `actions/accounts-list.md`, `actions/accounts-get.md`, `actions/messages-list.md`, `actions/messages-get.md`, or `actions/messages-clear.md` only when the task is mailbox-root administration or structural mailbox inspection.
- Use `actions/agent-binding-status.md`, `actions/agent-binding-register.md`, or `actions/agent-binding-unregister.md` only when the task is late mailbox binding for one existing local managed agent.
- Use the project mailbox lane when the operator explicitly wants `.houmao/mailbox` or the current active project overlay mailbox root.
- Use the arbitrary mailbox-root lane when the task targets one explicit filesystem mailbox root outside the project mailbox default.
- Route requests to remove all delivered emails while preserving mailbox accounts to `actions/clear-messages.md`; do not route that request to registration cleanup or account unregister.
- Route requests to remove delivered emails for one selected mailbox account while preserving other accounts to `actions/messages-clear.md`; do not route that request to all-account `clear-messages`, registration cleanup, or account unregister.
- Route requests to archive or export filesystem mailbox state to `actions/export.md`; preserve selected-account scope with repeated `--address` values and expose `--symlink-mode preserve` only when the user explicitly wants symlink preservation.
- Treat `project mailbox register` as manual mailbox-account administration, not as the default preparation step for every future mailbox-enabled easy launch.
- When the task is preparing a new specialist-backed easy instance whose same-root ordinary mailbox address will be derived from the managed-agent instance name, explain that the later `project agents launch --mail-transport filesystem --mail-root ...` step may own that address instead of preregistering it here.
- When the task is attaching mailbox support to an already-running local managed agent, route to `actions/agent-binding-register.md` instead of treating it as generic account registration.
- Treat Stalwart as a transport/bootstrap boundary, not as a peer `houmao-mgr mailbox ...` administration lane.

## Guardrails

- Do not guess missing required inputs that remain absent after checking the prompt and recent chat context.
- Do not route ordinary mailbox send, reply, list, peek, read, mark, move, archive, or live mailbox discovery through this skill.
- Do not route gateway notifier, reminder, or other live gateway-only state through this skill.
- Do not invent `houmao-mgr mailbox ...` filesystem root or account CRUD for Stalwart.
- Do not teach manual preregistration of the same `<agent-name>@houmao.localhost` address as the default precursor to same-root specialist-backed easy launch.
- Do not present structural message inspection as the same thing as actor-scoped unread or read follow-up state.
- Do not suggest `HOUMAO-<agentname>@houmao.localhost` as the ordinary mailbox-address pattern for a managed agent.
- Do not skip `command -v houmao-mgr` as the default first step unless the user explicitly requests a different launcher.
- Do not probe Pixi, repo-local `.venv`, or project-local `uv run` before the PATH check and uv fallback unless the user explicitly asks for one of those launchers.
- Do not hand-edit mailbox-root files when the maintained `houmao-mgr` surfaces already cover the task.
- Do not hand-author supported mailbox CLI commands from Markdown skeletons when a command template supports the surface.
- Do not use `mailbox cleanup` when the user asked to remove delivered email content while preserving accounts; use `mailbox clear-messages` or `project mailbox clear-messages` for all-account scope, and use `mailbox messages clear --address` or `project mailbox messages clear --address` for one selected account.
- Do not recommend ad hoc recursive mailbox-root copying when the maintained export command covers the request.
- Do not use deprecated `houmao-cli` or removed standalone CAO launcher workflows for mailbox administration.
