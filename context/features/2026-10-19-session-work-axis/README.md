# Session Work Axis

Status: Design draft

## Purpose

Add a session-scoped `work` axis to managed-agent tracked state so that "prompt-ready" no longer implies "all work done". Providers now let agents put work in the background and return control: the turn ends, the composer accepts input, the surface goes stable, and provider-acknowledged work is still running. The old conflation `prompt-ready == turn-terminal == task-terminal` no longer holds, and every consumer that relies on it needs to account for the split.

The axis is provider-neutral tracked state: `work = pending | clear | unknown`. The derived state `settled = (turn.phase == ready) AND (work == clear)` recovers the old "you can assign the next task" meaning explicitly. The CLI Hook Observation Channel is the primary delivery mechanism for `work` evidence; TUI corroboration is a later option if providers render reliable background indicators.

## Artifacts

- [Feature Requirement](feature-requirement.md)
- [ADR 0001: Three-Axis State Model](adrs/0001-three-axis-state-model.md)

## Current Stage

Feature requirement and the core state-model decision are drafted from the exploration session of 2026-10-19. Use cases, interface design, milestones, and implementation handoff remain to be written. Related plumbing decisions (collector, merge, admission gates) already live in the OpenSpec change `add-cli-hook-observation-channel`.

## Related Context

- [CLI Hook Observation Channel](../2026-10-18-cli-hook-observation-channel/README.md): the sibling feature that delivers hook evidence, including `Stop.background_tasks` and `session_crons` payloads.
- [OpenSpec change `add-cli-hook-observation-channel`](../../../openspec/changes/add-cli-hook-observation-channel/): approved-direction planning artifacts for the channel plumbing.
- [TUI Tracking State Model](../../../docs/reference/tui-tracking/state-model.md): the current `surface` / `turn` / `last_turn` vocabulary this feature extends.
- [Claude Parsing Repair Campaign](../../campaigns/debug/2026-10-12-claude-code-tui-parsing/reports/2026-10-12-claude-2-1-296-parsing-repair.md): the failure classes that motivate hook-driven facts.

## Open Questions

- Which provider events, if any, report background work starting and finishing at the Claude 2.1.296 floor? (Assigned to the hook channel spike, task 1.2.)
- Does a background-task completion wake an idle agent into a new turn, and does any hook fire for it?
- Does the provider TUI render a running-background indicator reliable enough for TUI corroboration of `work`?
- Final public field naming: `work.posture` versus a flat `work_pending` tristate.
- Which existing consumers (agent-loop skills, gateway surfaces, qualification labels, docs) assume prompt-ready means task-terminal, and what does each need?
- Should a stricter admission policy that requires `settled` ever exist, or do orchestrators gate on the field themselves?
