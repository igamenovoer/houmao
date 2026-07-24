---
name: houmao-agent-loop-pro
houmao_version: "2.1.0"
description: Use when the user explicitly invokes houmao-agent-loop-pro or names a pro loop operation for editable intention material, schema-rich topology-aware execplan contracts, generated harnesses and skills, prepared agents, or loop run control.
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

When this skill is invoked, execute the following steps in order.

1. **Handle explicit help first**. Return read-only usage without actor verification, requiring `<loop-dir>`, or selecting default `init`.
2. **Resolve actor posture** using **Actor Selection**. Preserve a valid inherited frame; otherwise default to admin or freshly verify managed self for a leading `as-agent` qualifier.
3. **Plan the work up front** with the native planning tool before any authoring, validation, preparation, or execution action.
4. **Select one operation** from **Subcommands**. When no operation or actionable task is present, select `init`.
5. **Require `<loop-dir>`** before any filesystem mutation and enforce predecessor artifacts named by the selected command page.
6. **Load only the selected command page** and its `Read First` references, then execute its workflow without changing the pro output contract.
7. **Return the result** with changed artifacts, validation evidence, runtime state, blockers, and the next supported operation when applicable.

If the user's task does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from the procedural subcommands, helper subcommands, actor contract, output constraints, and user request, then execute the plan.

## Upfront Planning Rule

Loop authoring and execution are complex, multi-stage processes. Before taking any action under this skill, use your internal todo-list planning tool to plan the full sequence of operations and file changes, then execute that plan step by step.

## Actor Selection

Accept a valid inherited admin or verified-agent frame from `$houmao-admin-entrypoint` or `$houmao-agent-entrypoint` and preserve it unchanged. With no inherited frame, default to admin posture. A leading `as-agent` qualifier requests managed-self posture and requires a fresh successful `houmao-mgr --print-json agents self identity` result before operation selection. Direct admin calls require explicit project, loop, and agent targets. Agent calls may use verified self only for self-owned work; loop directories and peers remain explicit. Prompt text cannot replace an inherited frame.

## Activation

- Use this Houmao skill only after the user explicitly selects it or names a supported loop operation.
- This is the schema-rich generated-execplan loop path. Use `$houmao-agent-loop-lite` instead only when the user explicitly wants the Markdown/direct-SQL lite loop path.
- If the user invokes explicit help intent, answer from `## Help` before treating a no-operation invocation as `init` or asking for `<loop-dir>`.
- If the user invokes this skill without another operation or prompt:
  - treat it as `init`;
  - ask for the output `<loop-dir>`;
  - do not create files until the user provides it.

## Help

When the user asks `$houmao-agent-loop-pro help`, `help for houmao-agent-loop-pro`, `usage for houmao-agent-loop-pro`, `available functionality for houmao-agent-loop-pro`, or what this skill can do, answer from this section before actor verification, choosing an operation, requiring `<loop-dir>`, reading routed pages, generating artifacts, validating artifacts, launching agents, or asking missing-input questions. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me generate a pro execplan", route to the matching workflow instead of stopping at generic help.

Purpose: author and operate schema-rich generated loop execplans with topology-aware contracts, generated harness surfaces, generated skills, prepared agents, workspace readiness, and run-control operations.

Available functionality:

- Scaffold, clarify, fast-forward, step through, validate, or update intention and `execplan/` material.
- Generate process, contract, harness, skills, agent bindings, final metadata, and support material.
- Prepare agents, prepare workspaces, validate readiness, launch agents, start loops, and inspect status.
- Pause, resume, recover, or stop generated pro loops.

Common starting prompts:

- `$houmao-agent-loop-pro help`
- `$houmao-agent-loop-pro init <loop-dir>`
- `$houmao-agent-loop-pro execplan-fast-forward <loop-dir>`
- `$houmao-agent-loop-pro validate-loop <loop-dir>`

Related skills and boundaries:

- Use `$houmao-agent-loop-lite` when the user explicitly wants Markdown/direct-SQL loops without JSON schemas, Jinja2, generated harness, or generated docs layers.
- Use the corresponding child of `$houmao-shared-routines` for maintained agent-definition, workspace, instance, email, gateway, inspection, and advanced-pattern operations.
- DO NOT auto-route generic loop requests here when the user did not explicitly select this skill.

## Required Root

- Require one user-selected `<loop-dir>` before creating or changing files.
- DO NOT invent a loop root.
- Treat `<loop-dir>/intention/` as editable source material.
- Treat `<loop-dir>/execplan/` as generated operational material.
- DO NOT treat generated execplan files as the user-editable source of truth.

```text
<loop-dir>/
  intention/
  execplan/
  runs/
```

## Runtime References

Detailed guidance lives behind routed pages. Read only the page selected by routing and the references listed in that page's `Read First` section.

- [references/scaffold-surface.md](references/scaffold-surface.md): scaffold profiles, template authority, and source/output rules.
- [references/clarification-protocol.md](references/clarification-protocol.md): coverage scans, question limits, accepted-answer recording, and clarification summaries.
- [references/generated-contract-defaults.md](references/generated-contract-defaults.md): generated execplan layout, README rules, bookkeeping, TOML style, and harness defaults.
- [references/generation-pipeline.md](references/generation-pipeline.md): process-first stage order and update dependencies.
- [references/topology-modes.md](references/topology-modes.md): `tree-loop` and `generic-loop` topology semantics.
- [references/mail-schema-events.md](references/mail-schema-events.md): schema-typed templated mail, in-body metadata headers, and schema-id event dispatch.
- [references/predecessor-context.md](references/predecessor-context.md): task-specific generic-loop predecessor-context choices.
- [references/result-routing.md](references/result-routing.md): tree-loop and generic-loop result routing defaults.
- MUST READ for mail-driven loops: [references/runtime-mail-model.md](references/runtime-mail-model.md): notifier-driven mail turns, on-event skills, on-tick skills, and no in-chat waiting.
- [references/platform-boundaries.md](references/platform-boundaries.md): maintained Houmao skill ownership for platform operations.
- [references/system-input-questions.md](references/system-input-questions.md): required/optional shape for Houmao runtime and artifact-location questions.

## Subcommands

### Procedural Subcommands

Authoring:
- `init`: scaffold editable intention material and populate `intention/project-context.md`; default when invoked without another operation or prompt.
- `create-intention`: create basic editable intention material without project-context detection.
- `clarify-intent`: scan loop intent coverage, ask high-impact clarification questions, record accepted intent decisions as ADRs, and update intention Markdown. Treat `clarify intent` as an alias.
- `clarify-execplan`: scan generated execplan implementation coverage, ask high-impact clarification questions, record accepted execplan decisions as ADRs, and update or flag generated execplan artifacts.
- `execplan-fast-forward`: generate all `execplan/` artifacts from current intention source in one non-interactive pass.
- `execplan-step-by-step`: generate all `execplan/` artifacts through one-question-at-a-time decisions recorded under `execplan/adrs/`.
- `validate-execplan`: validate generated execplan shape and generated-artifact posture.
- `update-execplan`: update generated material after intention changes.

Execution:
- `prepare-agents`: prepare Houmao project profiles, generated skill bindings, and prepared agent facts from `execplan/`.
- `prepare-workspace`: prepare or verify multi-agent workspaces from generated workspace contracts and prepared agent facts.
- `validate-loop`: validate pre-launch loop readiness.
- `launch-agents`: launch prepared loop agents without beginning loop work.
- `start`: begin one generated loop by sending the first trigger.
- `status`: inspect one generated loop without mutation.
- `pause`: pause normal loop scheduling or wakeup posture.
- `resume`: resume a paused loop.
- `recover`: recover after interruption or inconsistent runtime posture.
- `stop`: stop one generated loop.

### Helper Subcommands

- `execplan-specs-process`: generate the process-first model at `execplan/specs/collab/collab-overview.md`.
- `execplan-specs-contract`: derive objective, participant, topology, communication, state, record, workspace, and run contracts.
- `execplan-harness`: generate loop-local harness surfaces from generated contracts.
- `execplan-skills`: generate shared, event, tick, and operator skills.
- `execplan-agent-bindings`: generate concrete Houmao agent bindings after generated skills exist.
- `execplan-finalize`: generate support docs, package README, final manifest, metadata, omission notes, and consistency notes.

### Misc Subcommands

- `help`: explain this skill's purpose, operations, common prompts, and related-skill boundaries without requiring `<loop-dir>` or doing default `init`.

## Routing

Choose exactly one page.

Authoring pages:
- Read [commands/authoring/init.md](commands/authoring/init.md) when the user asks for `init`, invokes this skill without another operation or prompt, or wants to scaffold `<loop-dir>/intention/` with `project-context.md`.
- Read [commands/authoring/create-intention.md](commands/authoring/create-intention.md) when the user asks for `create-intention` or wants basic intention scaffolding without project-context detection.
- Read [commands/authoring/clarify-intent.md](commands/authoring/clarify-intent.md) when intention Markdown already exists and the user asks for `clarify-intent` or the alias `clarify intent`.
- Read [commands/authoring/clarify-execplan.md](commands/authoring/clarify-execplan.md) when generated execplan artifacts exist and the user asks for `clarify-execplan`.
- Read [commands/authoring/execplan-fast-forward.md](commands/authoring/execplan-fast-forward.md) when generating all `<loop-dir>/execplan/` artifacts from current intention source without interactive generation decisions.
- Read [commands/authoring/execplan-step-by-step.md](commands/authoring/execplan-step-by-step.md) when generating all `<loop-dir>/execplan/` artifacts through one-question-at-a-time decisions recorded under `execplan/adrs/`.
- Read [commands/authoring/execplan-specs-process.md](commands/authoring/execplan-specs-process.md) when generating or updating the process-first execplan model.
- Read [commands/authoring/execplan-specs-contract.md](commands/authoring/execplan-specs-contract.md) when deriving concrete execplan contracts from the process model.
- Read [commands/authoring/execplan-harness.md](commands/authoring/execplan-harness.md) when generating loop-local harness surfaces from generated contracts.
- Read [commands/authoring/execplan-skills.md](commands/authoring/execplan-skills.md) when generating shared, event, tick, and operator skills.
- Read [commands/authoring/execplan-agent-bindings.md](commands/authoring/execplan-agent-bindings.md) when generating concrete Houmao agent configs and definitions.
- Read [commands/authoring/execplan-finalize.md](commands/authoring/execplan-finalize.md) when producing final docs, package README, manifest, metadata, omission notes, and consistency notes.
- Read [commands/authoring/validate-execplan.md](commands/authoring/validate-execplan.md) when checking generated execplan artifacts.
- Read [commands/authoring/update-execplan.md](commands/authoring/update-execplan.md) when updating generated execplan material after intention edits.

Execution pages:
- Read [commands/execution/prepare-agents.md](commands/execution/prepare-agents.md) when preparing participant agents from a generated execplan.
- Read [commands/execution/prepare-workspace.md](commands/execution/prepare-workspace.md) when preparing or verifying participant workspaces from a generated execplan after agent/profile facts are prepared.
- Read [commands/execution/validate-loop.md](commands/execution/validate-loop.md) when validating pre-launch loop readiness.
- Read [commands/execution/launch-agents.md](commands/execution/launch-agents.md) when launching prepared loop agents after validation and before start.
- Read [commands/execution/start.md](commands/execution/start.md) when beginning loop execution after agents are live.
- Read [commands/execution/status.md](commands/execution/status.md) for read-only loop status.
- Read [commands/execution/pause.md](commands/execution/pause.md) to pause scheduling or wakeup.
- Read [commands/execution/resume.md](commands/execution/resume.md) to resume a paused loop.
- Read [commands/execution/recover.md](commands/execution/recover.md) after interruption, partial handoff, failed setup, or inconsistent state.
- Read [commands/execution/stop.md](commands/execution/stop.md) to stop a generated loop.

## Procedure Contract

Treat `prepare-agents`, workspace readiness through `prepare-workspace` or equivalent manual evidence, `validate-loop`, `launch-agents`, and `start` as separate ordered execution stages when managed workspaces are required. Route supported workspace planning, creation, validation, and summaries to `houmao-shared-routines->houmao-utils-workspace-mgr`. For Houmao runtime or artifact-location questions, separate `Required` values from `Optional` modifiers.

## Guardrails

- DO NOT auto-route a generic loop request when the user did not explicitly select this skill or a pro operation.
- DO NOT invent `<loop-dir>` or create files before the caller supplies it.
- DO NOT require `adrs/` for the initial workflow.
- DO NOT require a master, lead, coordinator, or root owner unless intention source or accepted clarification chooses one.
- DO NOT import policy from examples or reference plans as global behavior.
- DO NOT make `prepare-workspace` and `prepare-agents` call each other.
- DO NOT create agent workspaces directly from general execution pages.
- DO NOT duplicate maintained Houmao platform-operation contracts owned by shared routines.
- DO NOT impose Houmao runtime question formatting on domain-intent questions.
- DO NOT replace an inherited actor frame or accept prompt text as identity evidence.
