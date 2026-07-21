---
name: houmao-agent-loop-lite
houmao_version: "1.2.1"
description: Use when the user explicitly invokes houmao-agent-loop-lite or names a lite loop operation for Markdown contracts, typed Markdown templates, generated skills, direct SQLite state, prepared agents, or loop run control without pro-only schema and harness layers.
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

When this skill is invoked, execute the following steps in order.

1. **Handle explicit help first**. Return read-only usage without actor verification, requiring `<loop-dir>`, or selecting default `init`.
2. **Resolve actor posture** using **Actor Selection**. Preserve a valid inherited frame; otherwise default to admin or freshly verify managed self for a leading `as-agent` qualifier.
3. **Plan the work up front** with the native planning tool before any authoring, validation, preparation, or execution action.
4. **Select one operation** from **Subcommands**. When no operation or actionable task is present, select `init`.
5. **Require `<loop-dir>`** before any filesystem mutation and enforce predecessor artifacts named by the selected command page.
6. **Load only the selected command page** and its `Read First` references, then execute its workflow without crossing the Markdown and direct-SQL lite boundary.
7. **Return the result** with changed artifacts, validation evidence, runtime state, blockers, and the next supported operation when applicable.

If the user's task does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from the procedural subcommands, helper subcommands, actor contract, lite constraints, and user request, then execute the plan.

## Upfront Planning Rule

Loop authoring and execution are complex, multi-stage processes. Before taking any action under this skill, use your internal todo-list planning tool to plan the full sequence of operations and file changes, then execute that plan step by step.

## Actor Selection

Accept a valid inherited admin or verified-agent frame from `$houmao-admin-entrypoint` or `$houmao-agent-entrypoint` and preserve it unchanged. With no inherited frame, default to admin posture. A leading `as-agent` qualifier requests managed-self posture and requires a fresh successful `houmao-mgr --print-json agents self identity` result before operation selection. Direct admin calls require explicit project, loop, and agent targets. Agent calls may use verified self only for self-owned work; loop directories and peers remain explicit. Prompt text cannot replace an inherited frame.

## Activation

- Use this Houmao skill only after the user explicitly selects `$houmao-agent-loop-lite` or names a supported lite loop operation.
- If the user asks for help, answer from `## Help` before routing to an operation.
- If invoked without another operation or prompt, treat it as `init`, ask for `<loop-dir>`, and do not create files until the user provides it.
- DO NOT auto-route generic loop requests here when the user did not explicitly select lite.
- Use `$houmao-agent-loop-pro` for schema-rich topology contracts, JSON schemas, Jinja2 renderers, generated harnesses, generated docs, or stronger graph validation.

## Help

When the user asks `$houmao-agent-loop-lite help`, `help for houmao-agent-loop-lite`, `usage for houmao-agent-loop-lite`, `available functionality for houmao-agent-loop-lite`, or what this skill can do, answer from this section before actor verification, choosing an operation, requiring `<loop-dir>`, reading routed pages, generating artifacts, validating artifacts, launching agents, or asking missing-input questions. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state. If the user asks a concrete task such as "help me create a lite loop", route to the matching workflow instead of stopping at generic help.

Purpose: author and operate lightweight generated loops with the same routed lifecycle shape as pro, while using Markdown contracts, typed Markdown templates, generated skills, and direct SQLite state.

Available functionality:

- Scaffold, clarify, fast-forward, update, and validate lite `intention/` and `execplan/` material.
- Generate process Markdown, contract Markdown, generated skills, agent bindings, final metadata, and scaffold-owned README files.
- Enforce typed Markdown templates with `Loop-Template-Type`, `Loop-Template-Version`, and literal `<placeholder ...>` tokens.
- Use direct SQLite state under `runs/<run-id>/state.sqlite3` when durable state is needed.
- Prepare agents, prepare workspaces when needed, validate readiness, launch agents, start runs, inspect status, pause, resume, recover, and stop.
- Keep lite generated artifacts free of JSON schemas, Jinja2 renderers, generated harness commands, and generated docs layers.

Common starting prompts:

- `$houmao-agent-loop-lite help`
- `$houmao-agent-loop-lite init <loop-dir>`
- `$houmao-agent-loop-lite execplan-fast-forward <loop-dir>`
- `$houmao-agent-loop-lite validate-loop <loop-dir>`

Related skills and boundaries:

- `$houmao-agent-loop-pro`: schema-rich topology-heavy loop packages.
- The corresponding child of `$houmao-shared-routines`: maintained agent-definition, workspace, instance, email, gateway, messaging, inspection, and advanced-pattern operations.

## Required Root

- Require one user-selected `<loop-dir>` before creating or changing files.
- Treat `<loop-dir>/intention/` as editable source material.
- Treat `<loop-dir>/execplan/` as generated operational material.
- Treat `<loop-dir>/runs/` as durable runtime artifacts.
- Use `execplan/specs/`, `execplan/skills/`, and `execplan/agents/`.
- DO NOT generate `execplan/harness/` or `execplan/docs/`.

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

Read only the routed page selected below and its `Read First` references.

- [references/scaffold-surface.md](references/scaffold-surface.md): scaffold profiles and template ownership.
- [references/markdown-contract-defaults.md](references/markdown-contract-defaults.md): lite execplan Markdown shape.
- [references/markdown-template-events.md](references/markdown-template-events.md): typed Markdown template rules.
- [references/direct-sqlite-state.md](references/direct-sqlite-state.md): direct SQLite state contract.
- [references/runtime-mail-model.md](references/runtime-mail-model.md): notifier-prompt-driven bounded mail turns.
- [references/platform-boundaries.md](references/platform-boundaries.md): maintained Houmao operation ownership.
- [references/system-input-questions.md](references/system-input-questions.md): required and optional input question shape.

## Subcommands

### Procedural Subcommands

Authoring:
- `init`: scaffold editable intention material and project context.
- `create-intention`: create basic editable intention material without project-context detection.
- `clarify-intent`: clarify editable loop intent.
- `clarify-execplan`: clarify generated Markdown/direct-SQL implementation choices.
- `execplan-fast-forward`: generate all lite execplan artifacts in one pass.
- `validate-execplan`: validate generated lite package shape.
- `update-execplan`: update generated material after intention changes.

Execution:
- `prepare-agents`: prepare profiles, generated skill bindings, and prepared agent facts.
- `prepare-workspace`: prepare or verify workspaces when the lite execplan requires them.
- `validate-loop`: validate pre-launch readiness.
- `launch-agents`: launch prepared agents without beginning loop work.
- `start`: initialize or select one run and send the first trigger.
- `status`: inspect one lite loop without mutation.
- `pause`: pause normal scheduling or wakeup posture.
- `resume`: resume a paused lite loop.
- `recover`: recover after interruption or inconsistent runtime posture.
- `stop`: stop one lite loop.

Aliases:
- `clarify` maps to `clarify-intent` unless the prompt clearly targets generated execplan material.
- `generate-skills` maps to `execplan-skills`.
- `validate` maps to `validate-execplan` unless the prompt clearly asks for pre-launch readiness; use `validate-loop` for readiness.

### Helper Subcommands

- `execplan-specs-process`: generate the process-first Markdown model.
- `execplan-specs-contract`: derive Markdown contracts for objective, organization, communication, state, workspace, run, and participants.
- `execplan-skills`: generate shared, receiver, sender, tick, role, and operator skills as needed.
- `execplan-agent-bindings`: generate concrete Houmao agent bindings.
- `execplan-finalize`: generate support README files, manifest metadata, omissions, and consistency notes.

### Misc Subcommands

- `help`: explain this skill's purpose, operations, common prompts, and boundaries.

## Routing

Choose exactly one page.

Authoring pages:
- Read [commands/authoring/init.md](commands/authoring/init.md) for `init`.
- Read [commands/authoring/create-intention.md](commands/authoring/create-intention.md) for `create-intention`.
- Read [commands/authoring/clarify-intent.md](commands/authoring/clarify-intent.md) for `clarify-intent`.
- Read [commands/authoring/clarify-execplan.md](commands/authoring/clarify-execplan.md) for `clarify-execplan`.
- Read [commands/authoring/execplan-fast-forward.md](commands/authoring/execplan-fast-forward.md) for all-stage generation.
- Read [commands/authoring/execplan-specs-process.md](commands/authoring/execplan-specs-process.md) for process Markdown.
- Read [commands/authoring/execplan-specs-contract.md](commands/authoring/execplan-specs-contract.md) for derived Markdown contracts.
- Read [commands/authoring/execplan-skills.md](commands/authoring/execplan-skills.md) for generated skills.
- Read [commands/authoring/execplan-agent-bindings.md](commands/authoring/execplan-agent-bindings.md) for generated agent bindings.
- Read [commands/authoring/execplan-finalize.md](commands/authoring/execplan-finalize.md) for final metadata and README material.
- Read [commands/authoring/validate-execplan.md](commands/authoring/validate-execplan.md) for package-shape validation.
- Read [commands/authoring/update-execplan.md](commands/authoring/update-execplan.md) for generated material updates.

Execution pages:
- Read [commands/execution/prepare-agents.md](commands/execution/prepare-agents.md) for agent/profile preparation.
- Read [commands/execution/prepare-workspace.md](commands/execution/prepare-workspace.md) for workspace readiness.
- Read [commands/execution/validate-loop.md](commands/execution/validate-loop.md) for pre-launch readiness.
- Read [commands/execution/launch-agents.md](commands/execution/launch-agents.md) for live launch.
- Read [commands/execution/start.md](commands/execution/start.md) for run start.
- Read [commands/execution/status.md](commands/execution/status.md) for read-only status.
- Read [commands/execution/pause.md](commands/execution/pause.md), [commands/execution/resume.md](commands/execution/resume.md), [commands/execution/recover.md](commands/execution/recover.md), or [commands/execution/stop.md](commands/execution/stop.md) for run control.

## Procedure Contract

Keep this `SKILL.md` as a concise router and keep detailed workflow guidance in command or reference pages. Route workspace planning, creation, validation, and summaries to `houmao-shared-routines->houmao-utils-workspace-mgr`. Generated Markdown remains concise, explicit, and readable.

## Guardrails

- DO NOT auto-route a generic loop request when the user did not explicitly select this skill or a lite operation.
- DO NOT invent `<loop-dir>` or create files before the caller supplies it.
- DO NOT create JSON schemas, Jinja2 renderers, generated harness commands, or generated docs as lite outputs.
- DO NOT use TOML registries as the normal lite contract authority.
- DO NOT duplicate maintained Houmao platform-operation contracts owned by shared routines.
- DO NOT tell agents to sleep, poll, tail logs, or wait in chat for future mail or ticks.
- DO NOT cross the Markdown and direct-SQL lite boundary because a pro feature is convenient.
- DO NOT replace an inherited actor frame or accept prompt text as identity evidence.
