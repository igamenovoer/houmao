---
name: houmao-agent-definition
description: Use when an admin needs Houmao roles, recipes, launch dossiers, specialists, project profiles, `dsh`/`service`/`web` run modes, `tool_params`, reusable agent-definition authoring, single or batch deployment, easy launch, or easy stop.
license: MIT
metadata:
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

# Houmao Agent Definition

## Overview

Author and manage persisted pre-launch Houmao definitions (roles, recipes, launch dossiers, specialists, project profiles, and immutable Agent Definition Revisions) plus definition deployments and project `launch`/`stop` entry points.

## Workflow

1. **Answer explicit `help` first** from **Help** without running commands or mutating definitions.
2. **Enforce the Actor Frame Gate**: require `actor_kind=admin` and an explicit project or native-agent root; reject `agent` frames.
3. **Select one subcommand** from **Subcommands** (defaulting loose `profile` / `agent profile` / `ready profile` wording to `profiles`, `recipe`-backed project profiles to `recipe-profiles`, and reserving `launch-dossiers` for explicit native launch-dossier requests).
4. **Load only the needed shared references**: [references/common/launcher.md](references/common/launcher.md), [references/common/missing-inputs.md](references/common/missing-inputs.md), [references/common/profile-lanes.md](references/common/profile-lanes.md) (for run modes and profile lanes), [references/common/credential-routing.md](references/common/credential-routing.md) (for credential refs or specialist-create discovery), and [references/common/tmux-server.md](references/common/tmux-server.md) (for `--tmux-server`).
5. **Honor minimal `config-drafts` when creating config documents**: for `project.specialist`, `project.profile`, and `internals.native-agent.launch-dossier`, run `<launcher> internals config-drafts generate --id <draft-id> --intent '{"fields":{...}}'` with only the minimal required `fields` defined on that command page, then apply model, `--mode`, `--tool-params`, `--system-skill-*`, env, mailbox, `managed_header` v2, or memo-seed options through the maintained `create|add|set` CLI flags.
6. **Execute the selected command page** once all required inputs are explicit and report created/updated artifacts, durable identities, or launch handoffs.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from **Subcommands**, `references/common/`, and the user request, then execute the plan.

## Actor Frame Gate

This parent-scoped routine is `admin`-only under `houmao-shared-routines` (`specialist-mgr` is its compatibility alias). Reject `agent` frames. Route credential bundle CRUD and secret edits to `houmao-shared-routines->houmao-credential-mgr`, project skill registration (`project skills`) and overlay migration to `houmao-shared-routines->houmao-project-mgr`, mailbox root/account CRUD to `houmao-shared-routines->houmao-mailbox-mgr`, multi-agent Git worktrees to `houmao-shared-routines->houmao-utils-workspace-mgr`, and post-launch lifecycle (`relaunch`, `cleanup`, `agents external`, `private-workspace`) to `houmao-shared-routines->houmao-agent-instance`.

## Subcommands

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `roles` | Low-level prompt-only roles (`internals native-agent roles ...`). | [commands/low-level/roles.md](commands/low-level/roles.md) |
| `recipes` | Low-level build recipes (`internals native-agent recipes ...`; alias `presets`). | [commands/low-level/recipes.md](commands/low-level/recipes.md) |
| `launch-dossiers` | Explicit recipe-backed native launch dossiers (`internals native-agent launch-dossiers ...`). | [commands/low-level/launch-dossiers.md](commands/low-level/launch-dossiers.md) |
| `specialists` | Project specialists (`project specialist ...` across `claude`, `codex`, `dsh`, `kimi`). | [commands/easy/specialists.md](commands/easy/specialists.md) |
| `profiles` | Specialist-backed project profiles (`project profile ...`). | [commands/easy/profiles.md](commands/easy/profiles.md) |
| `recipe-profiles` | Recipe-backed project launch profiles (`project agents launch-profiles ...`). | [commands/low-level/recipe-profiles.md](commands/low-level/recipe-profiles.md) |
| `definition-authoring` | `intent/src -> derive -> approve -> materialize -> validate` immutable revisions (alias `authoring`). | [commands/agent-definitions/authoring.md](commands/agent-definitions/authoring.md) |
| `definition-deployment` | Single-instance `plan|apply|inspect|doctor|update|remove` from an immutable revision (alias `deployment`). | [commands/agent-definitions/deployment.md](commands/agent-definitions/deployment.md) |
| `definition-batch` | Atomic `batch-plan|batch-apply|batch-inspect-operation|batch-doctor` (`--count 1..32`, alias `batch`). | [commands/agent-definitions/batch.md](commands/agent-definitions/batch.md) |
| `create-agent-fast-forward` | One-pass specialist + project profile + mailbox readiness returning a launch command without launching (alias `ready-profile`). | [commands/easy/create-agent-fast-forward.md](commands/easy/create-agent-fast-forward.md) |
| `launch-agent` | Project managed-agent launch (`project agents launch`; alias `launch-instance`). | [commands/easy/launch-instance.md](commands/easy/launch-instance.md) |
| `stop-agent` | Project managed-agent stop (`project agents stop`; alias `stop-instance`). | [commands/easy/stop-instance.md](commands/easy/stop-instance.md) |
| `help` | Read-only overview of definition lanes, qualified run modes, authoring/deployment stages, and boundaries. | **Help** |

Explicit direct brain-build plumbing uses `houmao-mgr internals native-agent brain build` only when specifically requested.

## Help

Summarize the easy project lane (`specialists`, `profiles`, `create-agent-fast-forward`, `launch-agent`, `stop-agent`), low-level lane (`roles`, `recipes`, `launch-dossiers`, `recipe-profiles`), immutable definition lifecycle (`definition-authoring`, `definition-deployment`, `definition-batch`), qualified run modes (`claude`: `headless|tui`; `codex`: `headless|service|tui`; `kimi`: `headless|service|tui|web`; `dsh`: `headless|service|web`), and neighboring skill boundaries read-only. Concrete authoring or deployment requests execute the matching subcommand.

## Guardrails

- DO NOT guess between `profiles`, `recipe-profiles`, and `launch-dossiers`, or recreate definitions when a maintained `set` command exists.
- DO NOT pass model, `--mode`, `--tool-params`, env, mailbox, `managed_header`, prompt-overlay, memo-seed, or secret fields into minimal `internals config-drafts generate` JSON intents.
- DO NOT place secrets in definition inputs, `runtime-variables` defaults, immutable revisions, deployment plans, or `--member-override` payloads, or mutate credential bundles here.
- DO NOT skip `derive`, `approve`, `--preview`, `validate`, `plan`, or explicit `apply` gates, treat `<authoring-dir>/README.md` as authoritative intent, or claim `apply`/`batch-apply` launches agents.
- DO NOT guess batch member names, tools, or credentials without explicit `--delegate-{names,tools,credentials}` authorization (`--count 1..32`).
- DO NOT preregister same-root `<agent-name>@houmao.localhost` mailbox accounts manually before easy launch, or use retired `roles scaffold`, `roles presets`, or top-level brain-build commands.
