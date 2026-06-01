---
name: houmao-agent-loop-lite
description: Manual invocation only; use when explicitly requested as `houmao-agent-loop-lite` or through a named lite loop operation to author or operate pro-shaped Markdown/direct-SQL loop packages with typed Markdown templates, generated skills, and direct SQLite state, without JSON schemas, Jinja2, generated harnesses, or generated docs layers.
---

# Houmao Agent Loop Lite

## Activation

- Use this Houmao skill only after the user explicitly selects `houmao-agent-loop-lite` or names a supported lite loop operation.
- If the user asks for help, answer from `## Help` before routing to an operation.
- If invoked without another operation or prompt, treat it as `init`, ask for `<loop-dir>`, and do not create files until the user provides it.
- Do not auto-route generic loop requests here when the user did not explicitly select lite.
- Use `houmao-agent-loop-pro` for schema-rich topology contracts, JSON schemas, Jinja2 renderers, generated harnesses, generated docs, or stronger graph validation.

## Help

When the user asks `$houmao-agent-loop-lite help`, `help for houmao-agent-loop-lite`, `usage for houmao-agent-loop-lite`, `available functionality for houmao-agent-loop-lite`, or what this skill can do, answer from this section before choosing an operation, requiring `<loop-dir>`, reading routed pages, generating artifacts, validating artifacts, launching agents, or asking missing-input questions. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state. If the user asks a concrete task such as "help me create a lite loop", route to the matching workflow instead of stopping at generic help.

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

- `houmao-agent-loop-pro`: schema-rich topology-heavy loop packages.
- `houmao-agent-definition`, `houmao-utils-workspace-mgr`, `houmao-agent-instance`, `houmao-agent-email-comms`, `houmao-agent-gateway`, `houmao-agent-messaging`, and `houmao-agent-inspect`: maintained platform operations.
- `houmao-adv-usage-pattern`: elemental mailbox or gateway compositions outside generated loop packages.

## Required Root

- Require one user-selected `<loop-dir>` before creating or changing files.
- Treat `<loop-dir>/intention/` as editable source material.
- Treat `<loop-dir>/execplan/` as generated operational material.
- Treat `<loop-dir>/runs/` as durable runtime artifacts.
- Use `execplan/specs/`, `execplan/skills/`, and `execplan/agents/`.
- Do not generate `execplan/harness/` or `execplan/docs/`.

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

- [subskills/reference/scaffold-surface.md](subskills/reference/scaffold-surface.md): scaffold profiles and template ownership.
- [subskills/reference/markdown-contract-defaults.md](subskills/reference/markdown-contract-defaults.md): lite execplan Markdown shape.
- [subskills/reference/markdown-template-events.md](subskills/reference/markdown-template-events.md): typed Markdown template rules.
- [subskills/reference/direct-sqlite-state.md](subskills/reference/direct-sqlite-state.md): direct SQLite state contract.
- [subskills/reference/runtime-mail-model.md](subskills/reference/runtime-mail-model.md): notifier-prompt-driven bounded mail turns.
- [subskills/reference/platform-boundaries.md](subskills/reference/platform-boundaries.md): maintained Houmao operation ownership.
- [subskills/reference/system-input-questions.md](subskills/reference/system-input-questions.md): required and optional input question shape.

## Operations

Meta:
- `help`: explain this skill's purpose, operations, common prompts, and boundaries.

Authoring:
- `init`: scaffold editable intention material and project context.
- `create-intention`: create basic editable intention material without project-context detection.
- `clarify-intent`: clarify editable loop intent.
- `clarify-execplan`: clarify generated Markdown/direct-SQL implementation choices.
- `execplan-fast-forward`: generate all lite execplan artifacts in one pass.
- `execplan-specs-process`: generate the process-first Markdown model.
- `execplan-specs-contract`: derive Markdown contracts for objective, organization, communication, state, workspace, run, and participants.
- `execplan-skills`: generate shared, receiver, sender, tick, role, and operator skills as needed.
- `execplan-agent-bindings`: generate concrete Houmao agent bindings.
- `execplan-finalize`: generate support README files, manifest metadata, omissions, and consistency notes.
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

## Routing

Choose exactly one page.

Authoring pages:
- Read [subskills/authoring/init.md](subskills/authoring/init.md) for `init`.
- Read [subskills/authoring/create-intention.md](subskills/authoring/create-intention.md) for `create-intention`.
- Read [subskills/authoring/clarify-intent.md](subskills/authoring/clarify-intent.md) for `clarify-intent`.
- Read [subskills/authoring/clarify-execplan.md](subskills/authoring/clarify-execplan.md) for `clarify-execplan`.
- Read [subskills/authoring/execplan-fast-forward.md](subskills/authoring/execplan-fast-forward.md) for all-stage generation.
- Read [subskills/authoring/execplan-specs-process.md](subskills/authoring/execplan-specs-process.md) for process Markdown.
- Read [subskills/authoring/execplan-specs-contract.md](subskills/authoring/execplan-specs-contract.md) for derived Markdown contracts.
- Read [subskills/authoring/execplan-skills.md](subskills/authoring/execplan-skills.md) for generated skills.
- Read [subskills/authoring/execplan-agent-bindings.md](subskills/authoring/execplan-agent-bindings.md) for generated agent bindings.
- Read [subskills/authoring/execplan-finalize.md](subskills/authoring/execplan-finalize.md) for final metadata and README material.
- Read [subskills/authoring/validate-execplan.md](subskills/authoring/validate-execplan.md) for package-shape validation.
- Read [subskills/authoring/update-execplan.md](subskills/authoring/update-execplan.md) for generated material updates.

Execution pages:
- Read [subskills/execution/prepare-agents.md](subskills/execution/prepare-agents.md) for agent/profile preparation.
- Read [subskills/execution/prepare-workspace.md](subskills/execution/prepare-workspace.md) for workspace readiness.
- Read [subskills/execution/validate-loop.md](subskills/execution/validate-loop.md) for pre-launch readiness.
- Read [subskills/execution/launch-agents.md](subskills/execution/launch-agents.md) for live launch.
- Read [subskills/execution/start.md](subskills/execution/start.md) for run start.
- Read [subskills/execution/status.md](subskills/execution/status.md) for read-only status.
- Read [subskills/execution/pause.md](subskills/execution/pause.md), [subskills/execution/resume.md](subskills/execution/resume.md), [subskills/execution/recover.md](subskills/execution/recover.md), or [subskills/execution/stop.md](subskills/execution/stop.md) for run control.

## Constraints

- Keep `SKILL.md` as a router; put detailed workflow guidance in routed pages or references.
- Do not create JSON schemas, Jinja2 renderers, generated harness commands, or generated docs as lite outputs.
- Do not use TOML registries as the normal lite contract authority.
- Do not duplicate maintained Houmao platform-operation contracts.
- Route workspace planning, creation, validation, or summaries through `houmao-utils-workspace-mgr`.
- Do not tell agents to sleep, poll, tail logs, or wait in-chat for future mail or ticks.
- Keep generated Markdown concise, explicit, and readable.
