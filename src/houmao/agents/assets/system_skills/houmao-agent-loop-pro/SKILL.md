---
name: houmao-agent-loop-pro
description: Manual invocation only; use only when the user explicitly requests `houmao-agent-loop-pro` or an explicitly named pro loop operation to init editable loop-dir/intention material, generate or validate topology-aware loop-dir/execplan contracts, or execute a generated loop through authoring and execution subskills.
---

# Houmao Agent Loop Pro

## Activation

- Use this Houmao skill only after the user explicitly selects it or names a supported loop operation.
- This is the schema-rich generated-execplan loop path. Use `houmao-agent-loop-lite` instead only when the user explicitly wants the Markdown/direct-SQL lite loop path.
- If the user invokes explicit help intent, answer from `## Help` before treating a no-operation invocation as `init` or asking for `<loop-dir>`.
- If the user invokes this skill without another operation or prompt:
  - treat it as `init`;
  - ask for the output `<loop-dir>`;
  - do not create files until the user provides it.

## Help

When the user asks `$houmao-agent-loop-pro help`, `help for houmao-agent-loop-pro`, `usage for houmao-agent-loop-pro`, `available functionality for houmao-agent-loop-pro`, or what this skill can do, answer from this section before choosing an operation, requiring `<loop-dir>`, reading routed pages, generating artifacts, validating artifacts, launching agents, or asking missing-input questions. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me generate a pro execplan", route to the matching workflow instead of stopping at generic help.

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

- Use `houmao-agent-loop-lite` when the user explicitly wants Markdown/direct-SQL loops without JSON schemas, Jinja2, generated harness, or generated docs layers.
- Use `houmao-agent-definition`, `houmao-utils-workspace-mgr`, `houmao-agent-instance`, `houmao-agent-email-comms`, `houmao-agent-gateway`, and `houmao-agent-inspect` for maintained platform operations.
- Use `houmao-adv-usage-pattern` for elemental direct mailbox or gateway compositions outside generated loop packages.
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

- [subskills/reference/scaffold-surface.md](subskills/reference/scaffold-surface.md): scaffold profiles, template authority, and source/output rules.
- [subskills/reference/clarification-protocol.md](subskills/reference/clarification-protocol.md): coverage scans, question limits, accepted-answer recording, and clarification summaries.
- [subskills/reference/generated-contract-defaults.md](subskills/reference/generated-contract-defaults.md): generated execplan layout, README rules, bookkeeping, TOML style, and harness defaults.
- [subskills/reference/generation-pipeline.md](subskills/reference/generation-pipeline.md): process-first stage order and update dependencies.
- [subskills/reference/topology-modes.md](subskills/reference/topology-modes.md): `tree-loop` and `generic-loop` topology semantics.
- [subskills/reference/mail-schema-events.md](subskills/reference/mail-schema-events.md): schema-typed templated mail, in-body metadata headers, and schema-id event dispatch.
- [subskills/reference/predecessor-context.md](subskills/reference/predecessor-context.md): task-specific generic-loop predecessor-context choices.
- [subskills/reference/result-routing.md](subskills/reference/result-routing.md): tree-loop and generic-loop result routing defaults.
- MUST READ for mail-driven loops: [subskills/reference/runtime-mail-model.md](subskills/reference/runtime-mail-model.md): notifier-driven mail turns, on-event skills, on-tick skills, and no in-chat waiting.
- [subskills/reference/platform-boundaries.md](subskills/reference/platform-boundaries.md): maintained Houmao skill ownership for platform operations.
- [subskills/reference/system-input-questions.md](subskills/reference/system-input-questions.md): required/optional shape for Houmao runtime and artifact-location questions.

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
- `prepare-agents`: prepare Houmao easy profiles, generated skill bindings, and prepared agent facts from `execplan/`.
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
- Read [subskills/authoring/init.md](subskills/authoring/init.md) when the user asks for `init`, invokes this skill without another operation or prompt, or wants to scaffold `<loop-dir>/intention/` with `project-context.md`.
- Read [subskills/authoring/create-intention.md](subskills/authoring/create-intention.md) when the user asks for `create-intention` or wants basic intention scaffolding without project-context detection.
- Read [subskills/authoring/clarify-intent.md](subskills/authoring/clarify-intent.md) when intention Markdown already exists and the user asks for `clarify-intent` or the alias `clarify intent`.
- Read [subskills/authoring/clarify-execplan.md](subskills/authoring/clarify-execplan.md) when generated execplan artifacts exist and the user asks for `clarify-execplan`.
- Read [subskills/authoring/execplan-fast-forward.md](subskills/authoring/execplan-fast-forward.md) when generating all `<loop-dir>/execplan/` artifacts from current intention source without interactive generation decisions.
- Read [subskills/authoring/execplan-step-by-step.md](subskills/authoring/execplan-step-by-step.md) when generating all `<loop-dir>/execplan/` artifacts through one-question-at-a-time decisions recorded under `execplan/adrs/`.
- Read [subskills/authoring/execplan-specs-process.md](subskills/authoring/execplan-specs-process.md) when generating or updating the process-first execplan model.
- Read [subskills/authoring/execplan-specs-contract.md](subskills/authoring/execplan-specs-contract.md) when deriving concrete execplan contracts from the process model.
- Read [subskills/authoring/execplan-harness.md](subskills/authoring/execplan-harness.md) when generating loop-local harness surfaces from generated contracts.
- Read [subskills/authoring/execplan-skills.md](subskills/authoring/execplan-skills.md) when generating shared, event, tick, and operator skills.
- Read [subskills/authoring/execplan-agent-bindings.md](subskills/authoring/execplan-agent-bindings.md) when generating concrete Houmao agent configs and definitions.
- Read [subskills/authoring/execplan-finalize.md](subskills/authoring/execplan-finalize.md) when producing final docs, package README, manifest, metadata, omission notes, and consistency notes.
- Read [subskills/authoring/validate-execplan.md](subskills/authoring/validate-execplan.md) when checking generated execplan artifacts.
- Read [subskills/authoring/update-execplan.md](subskills/authoring/update-execplan.md) when updating generated execplan material after intention edits.

Execution pages:
- Read [subskills/execution/prepare-agents.md](subskills/execution/prepare-agents.md) when preparing participant agents from a generated execplan.
- Read [subskills/execution/prepare-workspace.md](subskills/execution/prepare-workspace.md) when preparing or verifying participant workspaces from a generated execplan after agent/profile facts are prepared.
- Read [subskills/execution/validate-loop.md](subskills/execution/validate-loop.md) when validating pre-launch loop readiness.
- Read [subskills/execution/launch-agents.md](subskills/execution/launch-agents.md) when launching prepared loop agents after validation and before start.
- Read [subskills/execution/start.md](subskills/execution/start.md) when beginning loop execution after agents are live.
- Read [subskills/execution/status.md](subskills/execution/status.md) for read-only loop status.
- Read [subskills/execution/pause.md](subskills/execution/pause.md) to pause scheduling or wakeup.
- Read [subskills/execution/resume.md](subskills/execution/resume.md) to resume a paused loop.
- Read [subskills/execution/recover.md](subskills/execution/recover.md) after interruption, partial handoff, failed setup, or inconsistent state.
- Read [subskills/execution/stop.md](subskills/execution/stop.md) to stop a generated loop.

## Constraints

- Do not auto-route generic loop requests here when the user did not explicitly select this skill.
- Do not invent `<loop-dir>`.
- Do not require `adrs/` for the initial workflow.
- Do not require a master, lead, coordinator, or root owner by default; generate central authority only when intention source or accepted clarification decisions choose it.
- Do not import policy from examples or reference plans as global behavior.
- Treat `prepare-agents`, workspace readiness through `prepare-workspace` or equivalent manual evidence, `validate-loop`, `launch-agents`, and `start` as separate ordered execution stages when managed workspaces are required.
- Do not make `prepare-workspace` and `prepare-agents` call each other.
- Do not create agent workspaces directly from general execution pages; use `houmao-utils-workspace-mgr` through `prepare-workspace` for supported workspace planning, creation, validation, and summaries.
- Do not duplicate maintained Houmao platform-operation contracts; route launch, messaging, mailbox, gateway, memory, lifecycle, and inspection work to their owning Houmao skills.
- When asking for Houmao runtime or artifact-location inputs, separate `Required` and `Optional` values. Do not impose that shape on user-task or domain-intent questions unless they ask for Houmao runtime behavior.
