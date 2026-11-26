---
name: houmao-admin-welcome
description: Use when a human operator explicitly invokes $houmao-admin-welcome for first-use orientation, route comparison, reorientation, command learning, or a guided tour; never select it implicitly.
license: MIT
metadata:
  houmao_version: "3.0.0"
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

# Houmao Admin Welcome

## Overview

Use this manual-only public skill after explicit `$houmao-admin-welcome ...` invocation. It provides read-only first-use orientation, route comparison, state-aware reorientation, command learning, and guided tours, then hands concrete execution to `$houmao-admin-entrypoint` with context preserved.

## Workflow

When this skill is invoked, execute the following steps in order.

1. **Handle explicit help first**: answer read-only from **Help Contract** and [commands/help.md](commands/help.md) before posture inspection or touring; treat concrete tasks (such as "help me stop agent X") as execution handoffs rather than generic help.
2. **Inspect current posture read-only**: follow [references/orientation.md](references/orientation.md) when narrow discovery materially improves the recommendation.
3. **Select one subcommand** from **Subcommands** (defaulting bare invocation to `start-guided-tour` with the state-appropriate menu in **No-Prompt Choices**).
4. **Load only the selected detail page** plus the needed section of [references/guided-paths.md](references/guided-paths.md), [references/concepts.md](references/concepts.md), or [references/question-style.md](references/question-style.md).
5. **Recommend one non-linear next step** so the operator can compare paths, explore a subsystem, inspect the command map, or continue an existing stage without restarting from `init`.
6. **Handoff concrete execution** via [references/admin-handoff.md](references/admin-handoff.md), preserving targets, confirmed choices, observed posture, and unresolved required inputs.

If the user's task does not map cleanly to these steps, use the native planning tool to build a bounded read-only orientation plan from the curated paths, subsystem map, supplied context, and user goal, then recommend one next invocation or ask for the smallest missing decision.

## Subcommands

Empty invocation selects `start-guided-tour`.

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `show-options` | Compare maintained guided paths and intended outcomes. | [commands/show-options.md](commands/show-options.md) |
| `choose-path` | Map an ambiguous goal and visible posture to one guided path. | [commands/choose-path.md](commands/choose-path.md) |
| `show-command-map` | Show public admin welcome, entrypoint, manual, and loop invocations without exposing shared children as standalone skills. | [commands/show-command-map.md](commands/show-command-map.md) |
| `next-step` | Recommend one state-aware continuation without restarting from project initialization. | [commands/next-step.md](commands/next-step.md) |
| `start-guided-tour` | Inspect read-only posture and begin the best-fitting guided path. | [commands/start-guided-tour.md](commands/start-guided-tour.md) |
| `help` | Explain welcome, its read-only boundary, guided paths, and execution handoff. | [commands/help.md](commands/help.md) |

## No-Prompt Choices

When no `.houmao/` project overlay exists, present these three choices:

1. **Create Houmao Project**: learn the project overlay, definitions, and first managed-agent path before authorizing execution.
2. **Subsystem Exploration**: browse project state, runtime control, communication, access/files, or multi-agent structure by concept.
3. **Inspect**: use read-only discovery to inspect the current workspace before choosing a path.

When project or runtime state already exists, preserve it and recommend **Existing Project Reorientation** or the nearest matching path stage rather than restarting from `init`.

## Curated Paths

- **Single Agent Full Run**: project overlay, tool/credential readiness (`claude`, `codex`, `dsh`, `kimi`), definition choice, run mode, launch, inspection, and follow-up.
- **Operator-Controlled Agent Team**: human orchestration across multiple agents, isolated workspaces, attributed `request` vs `prompt` vs mail vs `houmao-cccc`, and per-agent lifecycle.
- **Pro Agent Loop**: loop intent, `tree-loop` vs `generic-loop` topology, generated execplan stages, agent/workspace preparation, validation, and run control (offering `agent-loop-lite` for lightweight Markdown/SQLite loops).
- **Subsystem Exploration**: project/definitions, runtime/modes/executors, mail/gateway/`houmao-cccc`, access/versioned files/usage, and workspaces/loops/AG-UI.
- **Existing Project Reorientation**: summarize existing `.houmao/`, definitions, running or external agents, and continue from the nearest stage.

## Read-Only and Handoff Contract

Welcome may read maintained docs (including `houmao-mgr manual`), list non-secret state, and run narrow read-only checks from [references/orientation.md](references/orientation.md). Inferred intent only orders menu choices and never authorizes mutation. When concrete work is requested, emit the context-preserving `$houmao-admin-entrypoint <route> <operation>` block in [references/admin-handoff.md](references/admin-handoff.md) without executing it.

## Help Contract

Explicit help precedes posture inspection and summarizes the six subcommands, five curated paths, three blank-workspace choices, manual-only `$houmao-admin-welcome` activation, `houmao-mgr manual` operator docs, and `$houmao-admin-entrypoint` handoff.

## Guardrails

- DO NOT create or edit projects, credentials, definitions, skills, mailboxes, messages, gateways, access policies, workspaces, loop artifacts, or runtime state.
- DO NOT claim that welcome activates implicitly without `$houmao-admin-welcome`.
- DO NOT send requests, prompts, `houmao-cccc` chat, or mail, start or stop services, launch or stop agents, or adopt a session.
- DO NOT execute the `$houmao-admin-entrypoint` invocation that welcome recommends.
- DO NOT replace guided touring with a flat shared-routine dump.
- DO NOT treat inferred intent, examples, or menu selections as authorization for mutation.
- DO NOT drop confirmed targets or constraints when building an `$houmao-admin-entrypoint` handoff.
- DO NOT restart an existing project or running topology from `init` unless the operator explicitly asks.
