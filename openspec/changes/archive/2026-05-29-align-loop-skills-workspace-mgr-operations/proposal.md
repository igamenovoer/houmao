## Why

`houmao-utils-workspace-mgr` now exposes `plan`, `create`, `validate`, and `summarize`, but the loop skills still contain stale `execute` wording and older workspace-shape assumptions. Because loop skills route workspace preparation through the workspace manager, their contracts need to consume the new operation set and the untracked in-repo workspace layout without making the workspace manager loop-owned.

## What Changes

- Update `houmao-agent-loop-pro` workspace-preparation guidance to route workspace-manager operations as `plan`, `create`, `validate`, and optional `summarize`; keep `execute` only as a legacy alias when interpreting older generated material.
- Revise pro `prepare-workspace` guidance so workspace readiness can come from workspace-manager `validate`, a current workspace-manager summary/report, or explicit manual evidence.
- Align generated pro workspace contracts with the untracked in-repo workspace layout:
  - `<repo-root>/houmao-ws/<task-name>/shared-kb/` for cross-run shared task knowledge
  - `<repo-root>/houmao-ws/<task-name>/owner-states/<subdir>/...` for per-run task-owner bookkeeping
  - `<repo-root>/houmao-ws/<task-name>/<agent-name>/states/` for per-agent bookkeeping
- Add validation-command inputs to pro workspace contracts so project-scope readiness checks can be passed to workspace-manager `validate`.
- Update pro validation guidance to require `prepare-workspace` and generated workspace contracts to distinguish planned, created, validated, summarized, missing, and custom/manual workspace evidence.
- Update lite platform-boundary wording so generated lite loops route explicit workspace setup through workspace-manager planning, creation, validation, or summaries.
- Update packaged asset tests to guard the new loop-to-workspace-manager contract and remove stale `execute`/old-bookkeeping assertions.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-agent-loop-pro-skill`: Align pro workspace contract generation, `prepare-workspace`, validation guidance, and platform-boundary references with workspace-manager `plan`/`create`/`validate`/`summarize` operations and the untracked in-repo workspace layout.
- `houmao-agent-loop-lite-skill`: Align lite platform-boundary guidance with workspace-manager `plan`/`create`/`validate`/`summarize` operations.

## Impact

- Packaged skill assets under `src/houmao/agents/assets/system_skills/houmao-agent-loop-pro/`.
- Packaged skill asset `src/houmao/agents/assets/system_skills/houmao-agent-loop-lite/SKILL.md`.
- Tests that assert loop-pro/lite system-skill asset shape, workspace-manager routing wording, generated workspace contract examples, or validation guidance.
- No runtime Python API or CLI behavior changes are expected; this is packaged skill guidance and specification alignment.
