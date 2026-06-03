## Why

`houmao-touring` is currently described mostly as a first-time guided tour and its entry behavior leaves too much room for different agents to improvise different first-turn and branch-selection output. Recent design notes refine the skill into a guide for users who are not yet familiar with Houmao, including outcome-focused operators and developer-minded users inspecting subsystem logic.

## What Changes

- Revise `houmao-touring` audience language from strictly first-time users to users not yet familiar with Houmao, including first-run users, re-orienting operators, and developers exploring system behavior.
- Add an explicit two-lane coverage model:
  - fast path use cases for outcome-focused users,
  - subsystem exploration for component-minded users.
- Replace many narrow fast-path aliases with three use-case fast paths:
  - Single Agent Full Run,
  - Operator-Controlled Agent Team,
  - Pro Agent Loop.
- Add subsystem-exploration guidance that presents Houmao by component area without becoming a complete skill catalog or low-level command reference.
- Tighten user-facing presentation rules so the tour stays compact, includes adaptable presentation examples, reports operation result and critical status, offers next choices after each step, prefers small Markdown tables, and uses `more detail` for expanded explanation or raw evidence.
- Preserve existing routing ownership: the touring skill teaches, orients, and routes; direct-operation skills still own concrete command behavior, detailed workflows, command references, option catalogs, and validation rules.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-touring-skill`: revise packaged touring-skill requirements for audience, entry behavior, fast path use cases, subsystem exploration, and compact presentation style.

## Impact

- Packaged skill content under `src/houmao/agents/assets/system_skills/houmao-touring/`.
- Existing `houmao-touring-skill` OpenSpec requirements.
- Unit tests that assert packaged skill anchors and installed content.
- Design notes under `docs/design/` that inform the revised skill behavior.
