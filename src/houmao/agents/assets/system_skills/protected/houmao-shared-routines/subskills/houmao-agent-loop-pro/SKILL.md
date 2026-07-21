---
name: houmao-agent-loop-pro
description: Manual invocation only; use when an eligible public entrypoint routes an explicitly named pro loop operation to initialize editable loop intention material, generate or validate topology-aware execplan contracts, or execute a generated loop through its routed authoring and execution commands.
---

# Houmao Agent Loop Pro

## Upfront Planning Rule

Loop authoring and execution are complex, multi-stage processes. Before taking any action under this skill, use your internal todo-list planning tool to plan the full sequence of operations and file changes, then execute that plan step by step.

## Actor Frame Gate

This protected routine MUST NOT execute standalone. Require an immutable admin or verified-agent frame from the containing public entrypoint. The admin branch requires explicit project, loop, and agent targets. The agent branch requires freshly verified self identity and may use self only for self-owned loop work; loop directories and peers remain explicit. Missing or mismatched frames fail closed.

## Activation

- Use this Houmao skill only after the user explicitly selects it or names a supported loop operation.
- This is the schema-rich generated-execplan loop path. Use `<public-entrypoint>->houmao-shared-routines->agent-loop-lite` instead only when the user explicitly wants the Markdown/direct-SQL lite loop path.
- If the user invokes explicit help intent, answer from `## Help` before treating a no-operation invocation as `init` or asking for `<loop-dir>`.
- If the user invokes this skill without another operation or prompt:
  - treat it as `init`;
  - ask for the output `<loop-dir>`;
  - do not create files until the user provides it.

## Help

When the user asks `$<public-entrypoint> agent-loop-pro help`, `help for houmao-agent-loop-pro`, `usage for houmao-agent-loop-pro`, `available functionality for houmao-agent-loop-pro`, or what this skill can do, answer from this section before choosing an operation, requiring `<loop-dir>`, reading routed pages, generating artifacts, validating artifacts, launching agents, or asking missing-input questions. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me generate a pro execplan", route to the matching workflow instead of stopping at generic help.

Purpose: author and operate schema-rich generated loop execplans with topology-aware contracts, generated harness surfaces, generated skills, prepared agents, workspace readiness, and run-control operations.

Available functionality:

- Scaffold, clarify, fast-forward, step through, validate, or update intention and `execplan/` material.
- Generate process, contract, harness, skills, agent bindings, final metadata, and support material.
- Prepare agents, prepare workspaces, validate readiness, launch agents, start loops, and inspect status.
- Pause, resume, recover, or stop generated pro loops.

Common starting prompts:

- `$<public-entrypoint> agent-loop-pro help`
- `$<public-entrypoint> agent-loop-pro init <loop-dir>`
- `$<public-entrypoint> agent-loop-pro execplan-fast-forward <loop-dir>`
- `$<public-entrypoint> agent-loop-pro validate-loop <loop-dir>`

Related skills and boundaries:

- Use `<public-entrypoint>->houmao-shared-routines->agent-loop-lite` when the user explicitly wants Markdown/direct-SQL loops without JSON schemas, Jinja2, generated harness, or generated docs layers.
- Use `<public-entrypoint>->houmao-shared-routines->agent-definition`, `<public-entrypoint>->houmao-shared-routines->utils-workspace-mgr`, `<public-entrypoint>->houmao-shared-routines->agent-instance`, `<public-entrypoint>->houmao-shared-routines->agent-email-comms`, `<public-entrypoint>->houmao-shared-routines->agent-gateway`, and `<public-entrypoint>->houmao-shared-routines->agent-inspect` for maintained platform operations.
- Use `<public-entrypoint>->houmao-shared-routines->adv-usage-pattern` for elemental direct mailbox or gateway compositions outside generated loop packages.
- Do not auto-route generic loop requests here when the user did not explicitly select this skill.

## Required Root

- Require one user-selected `<loop-dir>` before creating or changing files.
- Do not invent a loop root.
- Treat `<loop-dir>/intention/` as editable source material.
- Treat `<loop-dir>/execplan/` as generated operational material.
- Do not treat generated execplan files as the user-editable source of truth.

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

## Operations

Meta:
- `help`: explain this skill's purpose, operations, common prompts, and related-skill boundaries without requiring `<loop-dir>` or doing default `init`.

Authoring:
- `init`: scaffold editable intention material and populate `intention/project-context.md`; default when invoked without another operation or prompt.
- `create-intention`: create basic editable intention material without project-context detection.
- `clarify-intent`: scan loop intent coverage, ask high-impact clarification questions, record accepted intent decisions as ADRs, and update intention Markdown. Treat `clarify intent` as an alias.
- `clarify-execplan`: scan generated execplan implementation coverage, ask high-impact clarification questions, record accepted execplan decisions as ADRs, and update or flag generated execplan artifacts.
- `execplan-fast-forward`: generate all `execplan/` artifacts from current intention source in one non-interactive pass.
- `execplan-step-by-step`: generate all `execplan/` artifacts through one-question-at-a-time decisions recorded under `execplan/adrs/`.
- `execplan-specs-process`: generate the process-first model at `execplan/specs/collab/collab-overview.md`.
- `execplan-specs-contract`: derive objective, participant, topology, communication, state, record, workspace, and run contracts.
- `execplan-harness`: generate loop-local harness surfaces from generated contracts.
- `execplan-skills`: generate shared, event, tick, and operator skills.
- `execplan-agent-bindings`: generate concrete Houmao agent bindings after generated skills exist.
- `execplan-finalize`: generate support docs, package README, final manifest, metadata, omission notes, and consistency notes.
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

## Constraints

- Do not auto-route generic loop requests here when the user did not explicitly select this skill.
- Do not invent `<loop-dir>`.
- Do not require `adrs/` for the initial workflow.
- Do not require a master, lead, coordinator, or root owner by default; generate central authority only when intention source or accepted clarification decisions choose it.
- Do not import policy from examples or reference plans as global behavior.
- Treat `prepare-agents`, workspace readiness through `prepare-workspace` or equivalent manual evidence, `validate-loop`, `launch-agents`, and `start` as separate ordered execution stages when managed workspaces are required.
- Do not make `prepare-workspace` and `prepare-agents` call each other.
- Do not create agent workspaces directly from general execution pages; use `<public-entrypoint>->houmao-shared-routines->utils-workspace-mgr` through `prepare-workspace` for supported workspace planning, creation, validation, and summaries.
- Do not duplicate maintained Houmao platform-operation contracts; route launch, messaging, mailbox, gateway, memory, lifecycle, and inspection work to their owning Houmao skills.
- When asking for Houmao runtime or artifact-location inputs, separate `Required` and `Optional` values. Do not impose that shape on user-task or domain-intent questions unless they ask for Houmao runtime behavior.
