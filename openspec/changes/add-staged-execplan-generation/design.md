## Context

The current authoring workflow names the execplan package layers but does not define a generation order. The mature team-loop example shows that many downstream artifacts depend on a process model: participants, routes, message families, state transitions, harness commands, generated skills, agent bindings, and final docs are all derived from how the loop moves work.

The new staged authoring model should expose enough subcommands for controlled partial generation without making users manage every file family manually.

## Goals / Non-Goals

**Goals:**

- Add six staged execplan generation subcommands with stable names.
- Make the loop process specification the first generated stage.
- Make `generate-execplan` run the stages in order.
- Make `update-execplan` rerun the appropriate stage range after intention changes.
- Keep each stage generic, optional-aware, and scoped to generated execplan material.

**Non-Goals:**

- Do not add runtime code or a deterministic generator implementation.
- Do not define domain-specific process stages, participants, messages, or record types.
- Do not replace `validate-execplan`; validation remains read-only and separate from generation.
- Do not expose one subcommand per directory or file.

## Decisions

1. Use six staged subcommands.

The staged authoring surface will be:

- `execplan-specs-process`
- `execplan-specs-contract`
- `execplan-harness`
- `execplan-skills`
- `execplan-agent-bindings`
- `execplan-finalize`

Six stages are enough to preserve dependency order while keeping the command surface readable. A larger set would mirror directories too closely; a smaller set would hide the important boundary between process semantics, derived contracts, and generated operational surfaces.

2. Make `execplan-specs-process` the anchor.

The first stage generates the canonical loop process model: phases, events, handoffs, tick responsibilities, ownership, terminal posture, recovery posture, and provisional participant/message/record families. Objective, participants, communication, state, workspace, harness, skills, agents, and docs are then derived from that process model.

Alternative considered: generate objective and participants first. That is reasonable for simple plans, but it makes process artifacts secondary even though process decisions determine most downstream contracts.

3. Keep `generate-execplan` and `update-execplan` as orchestration commands.

Users should normally call `generate-execplan`; staged commands exist for inspection, repair, and partial regeneration. `update-execplan` should determine whether to restart from the process stage or a later stage based on which intention inputs changed.

Alternative considered: require users to call each stage manually. That would increase control but make the common path too verbose.

4. Finalize last.

Human docs, README, final manifest, generated metadata, and explicit omission notes should be produced after all authoritative generated artifacts exist. The manifest may be seeded earlier, but it should be finalized last.

## Risks / Trade-offs

- Stage names feel like implementation detail -> Mitigation: keep `generate-execplan` as the common command and present staged commands as advanced authoring controls.
- Partial regeneration produces stale downstream artifacts -> Mitigation: each stage must name its prerequisites and downstream invalidation effects; `validate-execplan` should catch stale or missing generated artifacts.
- Process model overfits one reference loop -> Mitigation: define the process model in generic terms: phases, events, handoffs, ticks, ownership, state effects, completion, recovery, and unresolved decisions.
- Users edit generated intermediate files -> Mitigation: preserve the existing rule that `intention/` is source and generated execplan artifacts are replaceable.
