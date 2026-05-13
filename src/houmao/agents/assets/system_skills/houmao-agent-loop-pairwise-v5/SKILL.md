---
name: houmao-agent-loop-pairwise-v5
description: Manual invocation only; use only when the user explicitly requests `houmao-agent-loop-pairwise-v5` or an explicitly named loop operation to init editable loop-dir/intention material, generate or validate generated loop-dir/execplan contracts, or execute a generated loop through authoring and execution subskills.
---

# Houmao Agent Loop Pairwise

## Activation

- Use this Houmao skill only after the user explicitly selects it or names a supported loop operation.
- If the user invokes this skill without another operation or prompt:
  - treat it as `init`;
  - ask for the output `<loop-dir>`;
  - do not create files until the user provides it.

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
- MUST READ for mail-driven loops: [subskills/reference/runtime-mail-model.md](subskills/reference/runtime-mail-model.md): notifier-driven mail turns, on-event skills, on-tick skills, and no in-chat waiting.
- [subskills/reference/platform-boundaries.md](subskills/reference/platform-boundaries.md): maintained Houmao skill ownership for platform operations.

## Operations

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
- `prepare-agents`: prepare Houmao agents and skill bindings from `execplan/`.
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
- Do not import policy from examples or reference plans as global behavior.
- Treat `prepare-agents`, workspace readiness through `prepare-workspace` or equivalent manual evidence, `validate-loop`, `launch-agents`, and `start` as separate ordered execution stages when managed workspaces are required.
- Do not make `prepare-workspace` and `prepare-agents` call each other.
- Do not create agent workspaces directly from general execution pages; use `houmao-utils-workspace-mgr` through `prepare-workspace` for supported workspace planning and execution.
- Do not duplicate maintained Houmao platform-operation contracts; route launch, messaging, mailbox, gateway, memory, lifecycle, and inspection work to their owning Houmao skills.
