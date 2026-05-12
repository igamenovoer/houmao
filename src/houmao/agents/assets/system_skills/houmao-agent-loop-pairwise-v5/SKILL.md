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

- Preconditions:
  - require one user-selected `<loop-dir>` before creating or changing files;
  - do not invent a loop root.
- Source/output rule:
  - `intention/` is editable source material;
  - `execplan/` is generated operational material.

```text
<loop-dir>/
  intention/
    README.md
    loop-overview.md
    ...
  execplan/
    manifest.toml
    adrs/
    specs/
      objective/
      collab/
        collab-overview.md
      comms/
      state/
      workspace/
      run/
      participants/
    skills/
    agents/
    harness/
    docs/
```

Workspace rule:
- when a generated loop needs agent workspaces, route workspace planning and creation through `houmao-utils-workspace-mgr`;
- this skill may generate workspace contracts and an operator workspace-management skill;
- do not duplicate workspace-manager setup mechanics.

## Shared Scaffold Surface

- Use the packaged scaffold generator under `scripts/scaffold.py` and starter assets under `assets/scaffolds/` whenever this skill needs to materialize scaffold-owned starter files or directories.
- Run the packaged scaffold generator with `pixi run python` when executing it from this repository.
- Supported scaffold profiles:
  - `intention-init`: `intention/README.md` and `intention/loop-overview.md`
  - `execplan-shell`: initial `execplan/` directory shell and `manifest.toml` seed
  - `execplan-stepwise-shell`: same shell plus `execplan/adrs/`
  - `execplan-finalize-docs`: scaffold-owned `execplan/README.md` and named docs starters under `execplan/docs/`
  - `execplan-adr`: one `execplan/adrs/<index>-<slug>.md` record from the shared ADR template
- Treat these profiles and template assets as the authoritative starter surface for scaffold-owned files.
- Later stages may revise scaffold-owned generated files, but routed pages should not restate those starter file bodies independently.

## Default Generated Contract

Use these defaults unless intention source or accepted clarification decisions choose an equivalent or narrower shape. Any equivalent or omission must be indexed or explained in `manifest.toml`, generated docs, or validation notes.

Execplan scaffold:
- `manifest.toml` indexes generated artifacts, generated-source posture, and plan revision.
- `adrs/` records accepted execplan-generation decisions when `execplan-step-by-step` is used.
- `specs/collab/collab-overview.md` is the required process-first authority.
- `specs/` separates objective, collaboration, communication, state, workspace, run-artifact, and participant contracts when those concerns apply.
- `skills/` contains one flat directory of generated skills: `skills/<unique-skill-name>/SKILL.md`. Skill names must be unique after installation; encode purpose in the skill name or metadata, not in nested category directories.
- `agents/` binds concrete Houmao agents to participant instances, prompt sources, installed skills, notifier prompt text, and workspace policy.
- `harness/` exposes loop-local validation, dynamic lookup, rendering, query, and controlled record application through an explicit command registry.
- `docs/` explains generated contracts for humans but is not source authority; final docs live under named files, not loose unindexed notes.

Participant and state defaults:
- separate participant role templates, stable participant instances, and concrete agent bindings;
- do not force a fixed participant topology or role count;
- when durable bookkeeping is needed, default to compact records for plan metadata, process state, handoffs or exchanges, communication payload lifecycle, operator intent events, and generic events;
- generate task-specific records only from intention source or clarification decisions.

Skill and harness defaults:
- generated on-event skills handle one concrete incoming event or message family, perform one bounded role-owned action, then stop;
- generated on-tick skills handle scheduling, reconciliation, timeout, completion, or "what now" decisions by doing at most one pass, then stopping;
- generated skills query specs, state, or harness output for dynamic policy and runtime facts instead of copying constants into static prose;
- generated harnesses do not own mailbox delivery, managed-agent launch, gateway discovery, memory management, or workspace creation.

Workspace and run defaults:
- generated workspace contracts identify launch cwd, agent work roots, notes or knowledge paths, writable temp/artifact paths, shared resources, and read/write rules when applicable;
- generated execution preserves durable payloads, rendered outputs, send or reply responses, records, state files, logs, and evidence under a run artifact layout such as `<loop-dir>/runs/<run-id>/`;
- omit unused default layers when the manifest and generated docs make the omission explicit.

## Houmao Loop Runtime Model

- Houmao agents do not run a conventional always-awake loop inside one chat turn.
- The Houmao email/notifier system runs separately from the target agents.
- When notifier support detects open mail for an agent, it sends that agent a prompt.
- That prompt should guide the agent to:
  - check and process the relevant mail;
  - use the generated mail-received on-event skill for the matching message family when applicable;
  - call any required on-tick skill after mail processing when the generated loop wants follow-up scheduling, reconciliation, timeout, or completion work.
- Mail notification prompts are customizable and may include loop-specific instructions.
- On-tick skills are not periodic background loops:
  - they are invoked from a notifier or operator prompt turn;
  - they perform one bounded pass;
  - they stop.
- After processing mail and any requested tick, the agent finishes the chat turn and waits for the next notifier or operator prompt.
- Do not design generated agents to sleep, poll, tail logs, or wait in-chat for future work; in-chat waiting blocks later mail notification prompts from being handled.
- Do not rely on an external periodic driver to wake agents for ticks; model tick execution as prompt-triggered follow-up work.

## Communication Defaults

- Cross-agent participant communication defaults to Houmao mail unless the intention source explicitly requests a non-mail communication mechanism.
- Do not ask the user to decide whether ordinary participant handoffs should use mail when the intention source is silent.
- Clarify loop-specific communication facts:
  - routes;
  - message families;
  - payload fields;
  - reply expectations;
  - state or record effects.
- Generated loop material owns communication semantics:
  - participant routes;
  - message families;
  - structured payload schemas;
  - Markdown render templates;
  - reply expectations;
  - loop-local state or record effects caused by mail.

Maintained Houmao skills own mail mechanics:
- `houmao-mailbox-mgr` for mailbox setup, inspection, repair, cleanup, export, registration, and late mailbox binding.
- `houmao-agent-email-comms` for ordinary mail status, list, read, send, post, reply, mark, move, and archive operations.
- `houmao-process-emails-via-gateway` for notifier-driven open-mail rounds when the current round provides the gateway base URL.
- `houmao-agent-messaging` for managed-agent prompt, interrupt, mailbox handoff, and gateway-backed communication routing.
- `houmao-agent-gateway` for gateway lifecycle and gateway posture.

Generated loop skills must not implement:
- custom mailbox storage;
- custom mailbox state management;
- ad hoc gateway discovery;
- local substitutes for ordinary mail send, read, reply, and archive behavior owned by maintained Houmao skills.

## Operations

Authoring:
- `init`: scaffold the initial editable intention area through `intention-init`; this is the default when this skill is invoked without another operation or prompt.
- `create-intention`: create the initial editable intention area through `intention-init`.
- `clarify intent`: interview the user about loop intent, record accepted decisions as ADRs, and update intention Markdown.
- `refine-intention`: update existing intention Markdown from user edits or new direction.
- `execplan-fast-forward`: scaffold `execplan/` through `execplan-shell` and generate all `execplan/` artifacts from `intention/` in one non-interactive pass.
- `execplan-step-by-step`: scaffold `execplan/` through `execplan-stepwise-shell`, then generate all `execplan/` artifacts interactively while recording accepted decisions under `execplan/adrs/`.
- `execplan-specs-process`: generate the canonical process model first at `execplan/specs/collab/collab-overview.md`, including Python-style pseudocode with inline comments and a high-level Mermaid sequence graph.
- `execplan-specs-contract`: derive objective, participant, topology, communication, state, record, workspace, and run contracts from the process model.
- `execplan-harness`: generate loop-local harness surfaces from contracts.
- `execplan-skills`: generate shared, event, tick, and operator skills from process/contracts/harness.
- `execplan-agent-bindings`: generate concrete Houmao agent bindings after generated skills exist.
- `execplan-finalize`: use `execplan-finalize-docs` for scaffold-owned starters, then generate support docs, package README, final manifest, metadata, omission notes, and consistency notes.
- `validate-execplan`: validate generated execplan shape and generated-artifact posture.
- `update-execplan`: update generated material after intention changes.

Execution:
- `prepare-agents`: prepare Houmao agents and skill bindings from `execplan/`.
- `start`: start one generated loop.
- `status`: inspect one generated loop without mutation.
- `pause`: pause normal loop scheduling or wakeup posture.
- `resume`: resume a paused loop.
- `recover`: recover after interruption or inconsistent runtime posture.
- `stop`: stop one generated loop.

## Routing

Choose exactly one page:

Authoring pages:
- Read [subskills/authoring/create-intention.md](subskills/authoring/create-intention.md) when the user asks for `init`, invokes this skill without another operation or prompt, or wants to scaffold `<loop-dir>/intention/`.
- Read [subskills/authoring/clarify-intent.md](subskills/authoring/clarify-intent.md) when intention Markdown already exists and the user asks to `clarify intent` through decision questions and ADR capture.
- Read [subskills/authoring/refine-intention.md](subskills/authoring/refine-intention.md) when intention Markdown already exists and needs revision.
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
- Read [subskills/execution/start.md](subskills/execution/start.md) when starting loop execution.
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
- Do not treat `execplan/` as the user-editable source of truth.
- Do not create agent workspaces directly from these pages; use `houmao-utils-workspace-mgr` for workspace planning and execution.
- Do not duplicate maintained Houmao platform-operation contracts; route launch, messaging, mailbox, gateway, memory, lifecycle, and inspection work to their owning Houmao skills.
