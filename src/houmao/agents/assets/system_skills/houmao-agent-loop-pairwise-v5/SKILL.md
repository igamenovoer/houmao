---
name: houmao-agent-loop-pairwise-v5
description: Manual invocation only; use only when the user explicitly requests `houmao-agent-loop-pairwise-v5` or an explicitly named loop operation to init editable `<loop-dir>/intention/` material, generate or validate generated `<loop-dir>/execplan/` contracts, or execute a generated loop through authoring and execution subskills.
---

# Houmao Agent Loop Pairwise

## Activation

- Use this Houmao skill only when the user explicitly asks for `houmao-agent-loop-pairwise-v5` or names a supported loop operation.
- If the user invokes `houmao-agent-loop-pairwise-v5` without another operation or prompt:
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
    specs/
    skills/
    agents/
    harness/
    docs/
```

Workspace rule:
- when a generated loop needs agent workspaces, route workspace planning and creation through `houmao-utils-workspace-mgr`;
- this skill may generate workspace contracts and an operator workspace-management skill;
- do not duplicate workspace-manager setup mechanics.

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
- `init`: scaffold the initial editable intention area; this is the default when this skill is invoked without another operation or prompt.
- `create-intention`: create the initial editable intention area.
- `clarify intent`: interview the user about loop intent, record accepted decisions as ADRs, and update intention Markdown.
- `refine-intention`: update existing intention Markdown from user edits or new direction.
- `generate-execplan`: generate `execplan/` from `intention/`.
- `validate-execplan`: validate generated execplan shape and generated-artifact posture.
- `regenerate-execplan`: rebuild generated material after intention changes.

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
- Read [subskills/authoring/generate-execplan.md](subskills/authoring/generate-execplan.md) when generating `<loop-dir>/execplan/` from current intention source.
- Read [subskills/authoring/validate-execplan.md](subskills/authoring/validate-execplan.md) when checking generated execplan artifacts.
- Read [subskills/authoring/regenerate-execplan.md](subskills/authoring/regenerate-execplan.md) when replacing generated execplan material after intention edits.

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
