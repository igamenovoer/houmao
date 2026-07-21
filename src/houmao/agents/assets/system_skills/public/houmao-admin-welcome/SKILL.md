---
name: houmao-admin-welcome
houmao_version: "1.2.1"
description: Use when a newcomer or returning human operator asks what Houmao is for, which workflow fits a goal, how projects, definitions, managed agents, communication, workspaces, or loops fit together, or what read-only next step to take.
license: MIT
---

# Houmao Admin Welcome

## Overview

Use this independent public skill for first contact, route comparison, state-aware reorientation, command learning, and guided touring. Welcome is read-only. It teaches the Houmao model, uses narrow inspection when it materially improves a recommendation, and hands concrete work to `$houmao-admin-entrypoint` with context preserved.

## Workflow

When this skill is invoked, execute the following steps in order.

1. **Classify the request**. Distinguish orientation, comparison, or reorientation from a concrete task that belongs at the execution entrypoint.
2. **Inspect current posture read-only**. Use [references/orientation.md](references/orientation.md) only as needed to distinguish a blank workspace, an existing project, definitions, running managed agents, mail or gateway posture, and loop artifacts.
3. **Handle the default**. Treat empty invocation as `start-guided-tour`; introduce Houmao in the user's current context and present the state-appropriate menu from **No-Prompt Choices**.
4. **Select one subcommand** from **Subcommands**. Let the user's goal and visible posture determine the narrowest useful read-only routine.
5. **Load only its detail page** and the selected guided-path or concept reference. Preserve compact presentation and ask explanatory questions that state why an input matters.
6. **Recommend a non-linear next step**. Let the user compare, go deeper, switch paths, inspect the command map, or return to a previous concept without restarting the tour.
7. **Handoff concrete work** using [references/admin-handoff.md](references/admin-handoff.md). Preserve the selected path, targets, constraints, known posture, confirmed choices, and unresolved required inputs.

If the user's task does not map cleanly to these steps, use the native planning tool to build a bounded orientation plan from the curated paths, subsystem map, supplied context, read-only boundary, and user goal, then recommend one next invocation or ask for the smallest missing decision.

## Subcommands

These commands are peer read-only routines. Empty invocation selects `start-guided-tour`.

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `show-options` | Compare the maintained guided paths and their intended outcomes. | [commands/show-options.md](commands/show-options.md) |
| `choose-path` | Translate an ambiguous goal and current posture into one recommended guided path. | [commands/choose-path.md](commands/choose-path.md) |
| `show-command-map` | Show public admin welcome and execution invocations without exposing shared children as standalone skills. | [commands/show-command-map.md](commands/show-command-map.md) |
| `next-step` | Recommend one small state-aware continuation without restarting from project initialization. | [commands/next-step.md](commands/next-step.md) |
| `start-guided-tour` | Inspect read-only posture and begin the best-fitting guided path. | [commands/start-guided-tour.md](commands/start-guided-tour.md) |
| `help` | Explain welcome, its read-only boundary, guided paths, and execution handoff. | [commands/help.md](commands/help.md) |

## No-Prompt Choices

When no Houmao project overlay exists, show exactly these three choices:

1. **Create Houmao Project**: learn the project overlay, definitions, and first managed-agent path before authorizing execution.
2. **Subsystem Exploration**: browse project state, runtime control, communication, context and evidence, or multi-agent structure by concept.
3. **Inspect**: use read-only discovery to understand the current workspace before choosing a path.

When useful project or runtime state already exists, preserve it and recommend Existing Project Reorientation or the matching stage of another path. Do not restart from initialization by default.

## Curated Paths

The maintained paths are:

- **Single Agent Full Run**: project posture, definition choice, launch readiness, one managed agent, inspection, and follow-up.
- **Operator-Controlled Agent Team**: explicit human orchestration, multiple agent targets, communication choices, workspaces, and evidence.
- **Pro Agent Loop**: loop intent, topology, generated-execplan readiness, agent and workspace preparation, validation, and run control.
- **Subsystem Exploration**: project state, runtime control, communication, context and evidence, and multi-agent structure.
- **Existing Project Reorientation**: recognize useful existing state and continue from the nearest supported stage.

Read [references/guided-paths.md](references/guided-paths.md) only after selecting a path. Use [references/concepts.md](references/concepts.md) for concise vocabulary and [references/question-style.md](references/question-style.md) for informative questions.

## Fast-Path and Presentation Contract

Infer likely intent from explicit wording and current state, but use the guess only to order choices. It never authorizes an operation. Start with a compact current-posture statement, one recommended path, and a small choice set. Keep tables to four columns or fewer. Offer `more detail` rather than front-loading every subsystem. Explain the purpose of every required question and distinguish required inputs from optional refinements.

The tour is non-linear. Users may switch paths, inspect a subsystem, compare commands, revisit a concept, or request execution at any point. Existing definitions, managed agents, workspace material, mail posture, and loop artifacts remain useful evidence rather than reasons to reset.

## Read-Only Boundary

Welcome may read maintained documentation, list state, and run documented read-only discovery when the evidence materially improves a recommendation. Choosing a path, showing an example, or identifying a likely intent never authorizes mutation, network exposure, service changes, message delivery, agent launch, or a later confirmation gate.

If a concrete request reaches welcome, do not execute it. Build the complete `$houmao-admin-entrypoint <route> <operation>` handoff and carry forward every known target, constraint, decision, and blocker. Welcome remains independently useful even when its execution siblings are not installed.

## Help Contract

Explicit help is read-only and precedes posture inspection or default touring. Explain the six subcommands, five curated paths, blank-workspace choices, narrow implicit trigger, and context-preserving handoff. A concrete phrase such as “help me stop agent X” is an execution task, not generic help.

## Guardrails

- DO NOT create or edit projects, credentials, definitions, mailboxes, messages, gateways, workspaces, loop artifacts, or runtime state.
- DO NOT send prompts or mail, start or stop services, launch or stop agents, or adopt a session.
- DO NOT execute the public invocation that welcome recommends.
- DO NOT replace guided touring with a shallow shared-routine catalog.
- DO NOT present inferred intent, example text, or a selected menu item as authorization for mutation.
- DO NOT discard supplied context when handing concrete work to `$houmao-admin-entrypoint`.
- DO NOT restart an existing project or running topology from initialization unless the user explicitly chooses that path.
