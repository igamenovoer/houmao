---
name: houmao-agent-loop-pairwise-v5
description: Manual invocation only; use only when the user explicitly requests `houmao-agent-loop-pairwise-v5` or an explicitly named v5 loop operation to create editable `<loop-dir>/intention/` material, generate or validate generated `<loop-dir>/execplan/` contracts, or execute a generated v5 loop through authoring and execution subskills.
---

# Houmao Agent Loop Pairwise V5

Use this Houmao skill only when the user explicitly asks for `houmao-agent-loop-pairwise-v5` or names a v5 loop operation.

V5 is a general loop authoring and execution skill. It is not CUDA-specific, Hopper-specific, or tied to any business domain.

## Required Root

Before creating or changing files, require one user-selected `<loop-dir>`.

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

`intention/` is editable source material. `execplan/` is generated operational material.

## Operations

Authoring:
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
- Read [subskills/authoring/create-intention.md](subskills/authoring/create-intention.md) when the user has an intention and wants to initialize `<loop-dir>/intention/`.
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

## Boundaries

- Do not auto-route generic loop requests here when the user did not explicitly select v5.
- Do not invent `<loop-dir>`.
- Do not require `adrs/` for the initial workflow.
- Do not encode CUDA, Hopper, kernel-variant, timing, or domain-specific policy as global v5 behavior.
- Do not treat `execplan/` as the user-editable source of truth.
- Do not duplicate maintained Houmao platform-operation contracts; route launch, messaging, mailbox, gateway, memory, lifecycle, and inspection work to their owning Houmao skills.
