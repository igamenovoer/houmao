## Context

`houmao-manage-specialist` currently presents the easy-specialist workflow as specialist definition CRUD only, while `houmao-manage-agent-instance` owns managed runtime lifecycle. That split is internally clean, but it does not match the operator-facing easy-specialist mental model documented elsewhere in the repository, where creating a specialist and launching or stopping a specialist-backed instance are part of one workflow.

The requested change is not to merge the two skills fully. It is to let the specialist skill cover the natural specialist-scoped runtime entry points while still directing users toward `houmao-manage-agent-instance` for broader live-agent lifecycle work after those entry actions.

This change crosses packaged skill assets plus system-skill documentation, so the boundary needs to be stated normatively before implementation.

## Goals / Non-Goals

**Goals:**

- Let `houmao-manage-specialist` route specialist-scoped `launch` and `stop` actions.
- Preserve `houmao-manage-agent-instance` as the canonical live managed-agent lifecycle skill for general follow-up work.
- Require explicit user-facing handoff guidance from the specialist skill after specialist `launch` and `stop`.
- Update system-skill docs so they describe the overlap intentionally rather than as an accidental contradiction.

**Non-Goals:**

- Moving `join`, `list`, or `cleanup` into `houmao-manage-specialist`.
- Making `houmao-manage-specialist` a generic managed-agent lifecycle skill.
- Removing specialist-backed launch from `houmao-manage-agent-instance`.
- Changing the underlying CLI contracts for `houmao-mgr project easy instance launch`, `houmao-mgr project easy instance stop`, or `houmao-mgr agents stop`.

## Decisions

### Decision: `houmao-manage-specialist` grows by two specialist-scoped actions only

The specialist skill will expand from `create|list|get|remove` to `create|list|get|remove|launch|stop`.

Rationale:

- This matches the operator-facing easy-specialist lifecycle without collapsing the skill into a generic runtime controller.
- The added actions map cleanly to the project-easy specialist mental model.

Alternative considered:

- Keep `houmao-manage-specialist` CRUD-only and rely on documentation to point users at `houmao-manage-agent-instance`.
- Rejected because that preserves the current routing friction the change is meant to remove.

### Decision: specialist launch and stop use the project-easy instance surface

`houmao-manage-specialist launch` will use `houmao-mgr project easy instance launch`.

`houmao-manage-specialist stop` will use `houmao-mgr project easy instance stop`.

Rationale:

- These commands are the specialist/easy-instance lifecycle surface already documented for project-easy workflows.
- Using `project easy instance stop` keeps the stop action specialist-scoped instead of silently broadening it into generic live-agent targeting by id or canonical managed-agent name.

Alternative considered:

- Route specialist stop through `houmao-mgr agents stop`.
- Rejected because that would make the specialist skill depend on generic live-agent identity rather than the easy-instance surface it is meant to front.

### Decision: `houmao-manage-agent-instance` stays canonical for follow-up lifecycle work

The instance skill will continue to be described as the canonical skill for general live managed-agent lifecycle after the initial specialist-scoped `launch` or `stop` action.

Rationale:

- This preserves one clear place for join/list/cleanup and broader follow-up operations.
- It prevents the specialist skill from becoming a second full runtime-control surface with overlapping responsibilities.

Alternative considered:

- Treat both skills as equally authoritative for all instance lifecycle work.
- Rejected because it would blur routing, make docs harder to follow, and increase the chance of inconsistent future expansions.

### Decision: the specialist skill must emit explicit handoff guidance after launch and stop

After successfully handling specialist `launch` or `stop`, `houmao-manage-specialist` will tell the user that further agent management should go through `houmao-manage-agent-instance`.

Rationale:

- The user explicitly requested this notice.
- The notice turns the overlap into an intentional bridge instead of leaving the user to infer the next skill boundary.

Alternative considered:

- Mention the instance skill only in static documentation.
- Rejected because the requested behavior is contextual guidance at the point of use.

### Decision: ambiguity resolution remains mental-model based

`houmao-manage-specialist` should handle launch or stop only when the request is clearly about a specialist or easy instance. General managed-agent lifecycle requests remain with `houmao-manage-agent-instance`.

Rationale:

- This preserves the existing "ask before guessing" stance while allowing both skills to coexist.
- It avoids accidental routing of generic managed-agent requests into project-easy specialist workflows.

Alternative considered:

- Prefer `houmao-manage-specialist` for every launch or stop request whenever a specialist might exist.
- Rejected because that would make the specialist skill too greedy and would conflict with the canonical lifecycle role of the instance skill.

## Risks / Trade-offs

- [Skill overlap becomes confusing] → Require explicit post-action handoff text and update system-skill docs to describe the overlap intentionally.
- [The specialist skill expands into generic runtime control over time] → Limit the new scope to `launch` and `stop` only and keep `join`, `list`, and `cleanup` exclusively on the instance skill.
- [Routing becomes ambiguous for bare "stop agent" requests] → Preserve the requirement to ask before guessing unless the prompt clearly states specialist/easy-instance context.
- [Documentation drifts between README, CLI reference, and skill specs] → Modify the OpenSpec contracts for both runtime skills and the related documentation in the same change.

## Migration Plan

1. Update the packaged specialist-skill contract to include `launch` and `stop` plus the required post-action handoff notice.
2. Update the packaged instance-skill contract so it explicitly remains canonical for general follow-up lifecycle work without claiming strict exclusivity over specialist entry points.
3. Update README and CLI system-skill documentation to describe the revised relationship between the two skills.
4. Implement the packaged skill asset changes and add any new specialist action pages needed for `launch` and `stop`.

Rollback strategy:

- Revert the skill asset changes and restore the prior documentation/spec text that limits `houmao-manage-specialist` to CRUD-only specialist management.
- No on-disk migration is required because this change alters routed guidance rather than stored project data.

## Open Questions

- None at proposal time.
