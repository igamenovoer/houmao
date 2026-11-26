---
name: houmao-agent-loop-pro
description: Use when the user explicitly invokes houmao-agent-loop-pro or names a pro loop operation for editable intention material, schema-rich topology-aware execplan contracts, generated harnesses and skills, prepared agents, or loop run control.
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

# Houmao Agent Loop Pro

## Workflow

1. **Handle explicit help first**. Answer read-only usage queries from `## Help` without actor verification, `<loop-dir>` prompts, or default `init` selection.
2. **Resolve actor posture** via `## Actor Selection`. Preserve a valid inherited frame; otherwise default to admin posture or run a fresh `houmao-mgr --print-json agents self identity` check for a leading `as-agent` qualifier.
3. **Plan up front** with the native planning tool before authoring, validating, preparing, or executing any multi-stage loop work.
4. **Select one operation** from `## Subcommands` (`init` when no operation or actionable task is supplied).
5. **Require `<loop-dir>`** before any filesystem mutation and verify predecessor artifacts required by the routed command page.
6. **Load only the routed command page** and its `## Read First` references, then execute its workflow without altering the pro contract boundary.
7. **Report outcomes** with modified artifacts, validation evidence, runtime state, blockers, and the next supported stage.

If the user request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from the procedural subcommands, helper subcommands, actor contract, output constraints, and user request, then execute the plan.

## Actor Selection

Accept a valid inherited admin or verified-agent frame from `$houmao-admin-entrypoint` or `$houmao-agent-entrypoint` unchanged. Without an inherited frame, default to admin posture unless a leading `as-agent` qualifier requests managed-self posture, which requires a fresh successful `houmao-mgr --print-json agents self identity` call before operation selection. Admin calls require explicit project, loop, and agent targets; agent calls may use verified self only for self-owned work while keeping `<loop-dir>` and peer targets explicit.

## Activation And Help

Use this skill only when the user explicitly selects `$houmao-agent-loop-pro` or names a supported pro loop operation; use `$houmao-agent-loop-lite` when the user explicitly wants Markdown and direct-SQLite loops without JSON schemas, Jinja2 renderers, generated harnesses, or generated docs. If invoked without an operation or task prompt, select `init`, ask for `<loop-dir>`, and create no files until `<loop-dir>` is provided.

When the user asks `$houmao-agent-loop-pro help`, `usage for houmao-agent-loop-pro`, or what this skill can do, return read-only help without running commands or mutating files:
- **Purpose**: author and operate schema-rich generated loop execplans (`tree-loop` and `generic-loop`) with topology-aware contracts, generated harness commands, generated skills, prepared agents (`headless`, `service`, `tui`, `web`), workspace readiness, and run control.
- **Starting prompts**: `$houmao-agent-loop-pro help`, `$houmao-agent-loop-pro init <loop-dir>`, `$houmao-agent-loop-pro execplan-fast-forward <loop-dir>`, `$houmao-agent-loop-pro validate-loop <loop-dir>`.
- **Boundaries**: delegate maintained platform operations (definitions, workspaces, instances, access, files, mail, gateway, messaging, `houmao-cccc`, inspection, memory) to `$houmao-shared-routines`. Concrete task prompts such as "help me generate a pro execplan" route to the matching subcommand instead of generic help.

## Required Root

Require one explicit `<loop-dir>` before creating or editing files. Treat `<loop-dir>/intention/` as editable source material, `<loop-dir>/execplan/` as generated operational material, and `<loop-dir>/runs/` as runtime state:

```text
<loop-dir>/
  intention/
  execplan/
  runs/
```

## Runtime References

Load only the references listed in the active command page's `## Read First` section:
- [references/scaffold-surface.md](references/scaffold-surface.md): scaffold profiles, template authority, and source/output rules.
- [references/clarification-protocol.md](references/clarification-protocol.md): coverage scans, question limits, ADR recording, and summaries.
- [references/generated-contract-defaults.md](references/generated-contract-defaults.md): generated `execplan/` layout, README rules, TOML style, and harness defaults.
- [references/generation-pipeline.md](references/generation-pipeline.md): process-first stage order and update dependencies.
- [references/topology-modes.md](references/topology-modes.md) and [references/cycle-normalization.md](references/cycle-normalization.md): `tree-loop` and `generic-loop` topology and cycle rules.
- [references/mail-schema-events.md](references/mail-schema-events.md), [references/predecessor-context.md](references/predecessor-context.md), and [references/result-routing.md](references/result-routing.md): schema-typed templated mail, predecessor context, and result routing.
- [references/runtime-mail-model.md](references/runtime-mail-model.md) (mandatory for mail-driven loops): notifier-driven bounded turns, on-event/on-tick skills, and no in-chat waiting.
- [references/platform-boundaries.md](references/platform-boundaries.md), [references/git-worktree-readiness.md](references/git-worktree-readiness.md), and [references/system-input-questions.md](references/system-input-questions.md): Houmao routine ownership, Git worktree checks, and `Required` vs `Optional` runtime input questions.

## Subcommands

Choose and load only one command page for the active step.

### Procedural Subcommands

| Subcommand | Purpose | Detail |
| --- | --- | --- |
| `init` | Scaffold editable `intention/` material and populate `intention/project-context.md` (default when no operation is given). | [commands/authoring/init.md](commands/authoring/init.md) |
| `create-intention` | Create baseline editable `intention/` material without project-context detection. | [commands/authoring/create-intention.md](commands/authoring/create-intention.md) |
| `clarify-intent` | Scan intention coverage, ask high-impact questions, record intent ADRs, and update `intention/` (alias: `clarify intent`). | [commands/authoring/clarify-intent.md](commands/authoring/clarify-intent.md) |
| `clarify-execplan` | Scan generated `execplan/` implementation choices, record execplan ADRs, and update or flag generated artifacts. | [commands/authoring/clarify-execplan.md](commands/authoring/clarify-execplan.md) |
| `execplan-fast-forward` | Generate all `execplan/` stages from current `intention/` in one non-interactive pass. | [commands/authoring/execplan-fast-forward.md](commands/authoring/execplan-fast-forward.md) |
| `execplan-step-by-step` | Generate `execplan/` artifacts interactively with one-question-at-a-time ADRs under `execplan/adrs/`. | [commands/authoring/execplan-step-by-step.md](commands/authoring/execplan-step-by-step.md) |
| `validate-execplan` | Validate generated `execplan/` contract shape and artifact completeness. | [commands/authoring/validate-execplan.md](commands/authoring/validate-execplan.md) |
| `update-execplan` | Reconcile generated `execplan/` artifacts after `intention/` edits. | [commands/authoring/update-execplan.md](commands/authoring/update-execplan.md) |
| `prepare-agents` | Prepare Houmao project profiles, project skills, system-skill pack policy, and prepared agent facts from `execplan/`. | [commands/execution/prepare-agents.md](commands/execution/prepare-agents.md) |
| `prepare-workspace` | Prepare or verify multi-agent workspaces via `houmao-shared-routines->houmao-utils-workspace-mgr`. | [commands/execution/prepare-workspace.md](commands/execution/prepare-workspace.md) |
| `validate-loop` | Validate read-only pre-launch readiness across execplan, profiles, workspaces, and runtime bindings. | [commands/execution/validate-loop.md](commands/execution/validate-loop.md) |
| `launch-agents` | Launch prepared participants (`headless`, `service`, `tui`, `web`) without sending loop-start triggers. | [commands/execution/launch-agents.md](commands/execution/launch-agents.md) |
| `start` | Begin one generated loop run by sending the initial trigger to live participants. | [commands/execution/start.md](commands/execution/start.md) |
| `status` | Inspect one generated loop run without mutating state. | [commands/execution/status.md](commands/execution/status.md) |
| `pause` | Pause loop scheduling or wakeup posture. | [commands/execution/pause.md](commands/execution/pause.md) |
| `resume` | Resume a paused loop run. | [commands/execution/resume.md](commands/execution/resume.md) |
| `recover` | Diagnose and recover after interruption, failed setup, or inconsistent runtime posture. | [commands/execution/recover.md](commands/execution/recover.md) |
| `stop` | Stop one generated loop run cleanly. | [commands/execution/stop.md](commands/execution/stop.md) |

### Helper Subcommands

| Subcommand | Purpose | Detail |
| --- | --- | --- |
| `execplan-specs-process` | Generate the process-first collaboration model at `execplan/specs/collab/collab-overview.md`. | [commands/authoring/execplan-specs-process.md](commands/authoring/execplan-specs-process.md) |
| `execplan-specs-contract` | Derive objective, participant, topology, communication, state, record, workspace, and run contracts. | [commands/authoring/execplan-specs-contract.md](commands/authoring/execplan-specs-contract.md) |
| `execplan-harness` | Generate loop-local deterministic harness commands from derived contracts. | [commands/authoring/execplan-harness.md](commands/authoring/execplan-harness.md) |
| `execplan-skills` | Generate shared, on-event, on-tick, and operator loop skills. | [commands/authoring/execplan-skills.md](commands/authoring/execplan-skills.md) |
| `execplan-agent-bindings` | Generate concrete Houmao participant-to-agent binding definitions after skills exist. | [commands/authoring/execplan-agent-bindings.md](commands/authoring/execplan-agent-bindings.md) |
| `execplan-finalize` | Generate support docs, package README, `execplan/manifest.toml`, omission notes, and consistency notes. | [commands/authoring/execplan-finalize.md](commands/authoring/execplan-finalize.md) |

### Misc Subcommands

| Subcommand | Purpose | Detail |
| --- | --- | --- |
| `help` | Explain purpose, operations, starting prompts, and boundaries without `<loop-dir>` or state changes. | `## Activation And Help` above |

## Procedure Contract

Keep `prepare-agents`, `prepare-workspace` (or explicit manual workspace evidence), `validate-loop`, `launch-agents`, and `start` as distinct ordered execution stages. Delegate workspace topology operations to `houmao-shared-routines->houmao-utils-workspace-mgr` and format Houmao runtime or artifact-location prompts with explicit `Required` vs `Optional` fields.

## Guardrails

- DO NOT auto-route generic loop requests here unless the user explicitly selects `$houmao-agent-loop-pro` or names a pro loop operation.
- DO NOT invent `<loop-dir>`, create files before `<loop-dir>` is provided, or treat generated `execplan/` files as hand-edited source of truth.
- DO NOT require `adrs/` during initial scaffolding or require a central lead/coordinator unless chosen by `intention/` or accepted clarification.
- DO NOT import domain policy from reference examples as global defaults or apply runtime question formatting to domain-intent questions.
- DO NOT make `prepare-agents` and `prepare-workspace` invoke each other or create agent workspaces directly outside `houmao-shared-routines->houmao-utils-workspace-mgr`.
- DO NOT duplicate maintained Houmao platform mechanics owned by `$houmao-shared-routines`.
- DO NOT instruct agents to sleep, poll, tail logs, or wait in-chat for future mail or ticks; rely on notifier-driven turns and explicit prompts.
- DO NOT replace an inherited actor frame or accept prompt text as identity evidence.
