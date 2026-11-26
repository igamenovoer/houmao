---
name: houmao-agent-loop-lite
description: Use when the user explicitly invokes houmao-agent-loop-lite or names a lite loop operation for Markdown contracts, typed Markdown templates, generated skills, direct SQLite state, prepared agents, or loop run control without pro-only schema and harness layers.
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

# Houmao Agent Loop Lite

## Workflow

1. **Handle explicit help first**. Answer read-only usage queries from `## Activation And Help` without actor verification, `<loop-dir>` prompts, or default `init` selection.
2. **Resolve actor posture** via `## Actor Selection`. Preserve a valid inherited frame; otherwise default to admin posture or run a fresh `houmao-mgr --print-json agents self identity` check for a leading `as-agent` qualifier.
3. **Plan up front** with the native planning tool before authoring, validating, preparing, or executing any multi-stage loop work.
4. **Select one operation** from `## Subcommands` (`init` when no operation or actionable task is supplied).
5. **Require `<loop-dir>`** before any filesystem mutation and verify predecessor artifacts required by the routed command page.
6. **Load only the routed command page** and its `## Read First` references, executing within the Markdown and direct-SQLite lite boundary.
7. **Report outcomes** with modified artifacts, validation evidence, runtime state, blockers, and the next supported stage.

If the user request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from the procedural subcommands, helper subcommands, actor contract, lite constraints, and user request, then execute the plan.

## Actor Selection

Accept a valid inherited admin or verified-agent frame from `$houmao-admin-entrypoint` or `$houmao-agent-entrypoint` unchanged. Without an inherited frame, default to admin posture unless a leading `as-agent` qualifier requests managed-self posture, which requires a fresh successful `houmao-mgr --print-json agents self identity` call before operation selection. Admin calls require explicit project, loop, and agent targets; agent calls may use verified self only for self-owned work while keeping `<loop-dir>` and peer targets explicit.

## Activation And Help

Use this skill only when the user explicitly selects `$houmao-agent-loop-lite` or names a supported lite loop operation; use `$houmao-agent-loop-pro` when schema-rich topology contracts, JSON schemas, Jinja2 renderers, generated harnesses, or generated docs are required. If invoked without an operation or task prompt, select `init`, ask for `<loop-dir>`, and create no files until `<loop-dir>` is provided.

When the user asks `$houmao-agent-loop-lite help`, `usage for houmao-agent-loop-lite`, or what this skill can do, return read-only help without running commands or mutating files:
- **Purpose**: author and operate lightweight generated loops using Markdown contracts, typed Markdown templates (`Loop-Template-Type`, `Loop-Template-Version`, literal `<placeholder ...>` tokens), generated skills, and direct SQLite state (`runs/<run-id>/state.sqlite3`) without JSON schemas, Jinja2, TOML registries, generated harnesses, or generated docs.
- **Starting prompts**: `$houmao-agent-loop-lite help`, `$houmao-agent-loop-lite init <loop-dir>`, `$houmao-agent-loop-lite execplan-fast-forward <loop-dir>`, `$houmao-agent-loop-lite validate-loop <loop-dir>`.
- **Boundaries**: delegate maintained platform operations to `$houmao-shared-routines`. Concrete task prompts such as "help me create a lite loop" route to the matching subcommand instead of generic help.

## Required Root

Require one explicit `<loop-dir>` before creating or editing files. Treat `<loop-dir>/intention/` as editable source, `<loop-dir>/execplan/` (`specs/`, `skills/`, `agents/` only, never `harness/` or `docs/`) as generated operational material, and `<loop-dir>/runs/` as durable runtime state:

```text
<loop-dir>/
  intention/
  execplan/
    specs/
    skills/
    agents/
  runs/
```

## Runtime References

Load only the references listed in the active command page's `## Read First` section:
- [references/scaffold-surface.md](references/scaffold-surface.md): scaffold profiles and template ownership.
- [references/markdown-contract-defaults.md](references/markdown-contract-defaults.md): lite `execplan/` Markdown shape.
- [references/markdown-template-events.md](references/markdown-template-events.md): typed Markdown template rules (`Loop-Template-Type`, `Loop-Template-Version`).
- [references/direct-sqlite-state.md](references/direct-sqlite-state.md): direct `runs/<run-id>/state.sqlite3` contract.
- [references/runtime-mail-model.md](references/runtime-mail-model.md): notifier-prompt-driven bounded mail turns.
- [references/platform-boundaries.md](references/platform-boundaries.md): maintained Houmao routine ownership.
- [references/system-input-questions.md](references/system-input-questions.md): `Required` and `Optional` runtime input question shape.

## Subcommands

Choose and load only one command page for the active step. Supported aliases: `clarify` maps to `clarify-intent` (unless targeting generated `execplan/` material), `generate-skills` maps to `execplan-skills`, and `validate` maps to `validate-execplan` (or `validate-loop` when asking for pre-launch readiness).

### Procedural Subcommands

| Subcommand | Purpose | Detail |
| --- | --- | --- |
| `init` | Scaffold editable `intention/` material and project context (default when no operation is given). | [commands/authoring/init.md](commands/authoring/init.md) |
| `create-intention` | Create baseline editable `intention/` material without project-context detection. | [commands/authoring/create-intention.md](commands/authoring/create-intention.md) |
| `clarify-intent` | Clarify editable loop intent and record accepted decisions (alias: `clarify`). | [commands/authoring/clarify-intent.md](commands/authoring/clarify-intent.md) |
| `clarify-execplan` | Clarify generated Markdown and direct-SQLite implementation choices. | [commands/authoring/clarify-execplan.md](commands/authoring/clarify-execplan.md) |
| `execplan-fast-forward` | Generate all lite `execplan/` stages in one non-interactive pass. | [commands/authoring/execplan-fast-forward.md](commands/authoring/execplan-fast-forward.md) |
| `validate-execplan` | Validate generated lite package shape and Markdown contracts (alias: `validate`). | [commands/authoring/validate-execplan.md](commands/authoring/validate-execplan.md) |
| `update-execplan` | Reconcile generated `execplan/` Markdown after `intention/` edits. | [commands/authoring/update-execplan.md](commands/authoring/update-execplan.md) |
| `prepare-agents` | Prepare profiles, generated skill bindings, and participant facts (`headless`, `service`, `tui`, `web`). | [commands/execution/prepare-agents.md](commands/execution/prepare-agents.md) |
| `prepare-workspace` | Prepare or verify workspaces via `houmao-shared-routines->houmao-utils-workspace-mgr` when required. | [commands/execution/prepare-workspace.md](commands/execution/prepare-workspace.md) |
| `validate-loop` | Validate read-only pre-launch readiness (readiness target for alias `validate`). | [commands/execution/validate-loop.md](commands/execution/validate-loop.md) |
| `launch-agents` | Launch prepared participants (`headless`, `service`, `tui`, `web`) without sending loop-start triggers. | [commands/execution/launch-agents.md](commands/execution/launch-agents.md) |
| `start` | Initialize or select `runs/<run-id>/` and send the first trigger. | [commands/execution/start.md](commands/execution/start.md) |
| `status` | Inspect one lite loop run without mutating state. | [commands/execution/status.md](commands/execution/status.md) |
| `pause` | Pause scheduling or wakeup posture. | [commands/execution/pause.md](commands/execution/pause.md) |
| `resume` | Resume a paused lite loop run. | [commands/execution/resume.md](commands/execution/resume.md) |
| `recover` | Diagnose and recover after interruption or inconsistent runtime posture. | [commands/execution/recover.md](commands/execution/recover.md) |
| `stop` | Stop one lite loop run cleanly. | [commands/execution/stop.md](commands/execution/stop.md) |

### Helper Subcommands

| Subcommand | Purpose | Detail |
| --- | --- | --- |
| `execplan-specs-process` | Generate the process-first Markdown model. | [commands/authoring/execplan-specs-process.md](commands/authoring/execplan-specs-process.md) |
| `execplan-specs-contract` | Derive Markdown contracts for objective, organization, communication, state, workspace, run, and participants. | [commands/authoring/execplan-specs-contract.md](commands/authoring/execplan-specs-contract.md) |
| `execplan-skills` | Generate shared, receiver, sender, tick, role, and operator skills (alias: `generate-skills`). | [commands/authoring/execplan-skills.md](commands/authoring/execplan-skills.md) |
| `execplan-agent-bindings` | Generate concrete Houmao participant bindings at `execplan/agents/bindings.md`. | [commands/authoring/execplan-agent-bindings.md](commands/authoring/execplan-agent-bindings.md) |
| `execplan-finalize` | Generate scaffold READMEs, `execplan/manifest.md`, omissions, and consistency notes. | [commands/authoring/execplan-finalize.md](commands/authoring/execplan-finalize.md) |

### Misc Subcommands

| Subcommand | Purpose | Detail |
| --- | --- | --- |
| `help` | Explain purpose, operations, starting prompts, and boundaries without `<loop-dir>` or state changes. | `## Activation And Help` above |

## Procedure Contract

Keep `SKILL.md` as a concise router, delegate workspace planning/creation/validation/summaries to `houmao-shared-routines->houmao-utils-workspace-mgr`, and keep all generated lite contracts concise, explicit Markdown.

## Guardrails

- DO NOT auto-route generic loop requests here unless the user explicitly selects `$houmao-agent-loop-lite` or names a lite loop operation.
- DO NOT invent `<loop-dir>` or create files before `<loop-dir>` is provided.
- DO NOT generate JSON schemas, Jinja2 renderers, `execplan/harness/` commands, `execplan/docs/`, or TOML contract registries as lite outputs.
- DO NOT cross the Markdown and direct-SQLite (`runs/<run-id>/state.sqlite3`) boundary for pro-only convenience.
- DO NOT duplicate maintained Houmao platform mechanics owned by `$houmao-shared-routines`.
- DO NOT instruct agents to sleep, poll, tail logs, or wait in-chat for future mail or ticks.
- DO NOT replace an inherited actor frame or accept prompt text as identity evidence.
