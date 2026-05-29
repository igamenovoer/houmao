## Why

The current in-repo workspace contract still treats parts of `houmao-ws` as Git-oriented shared knowledge and merge surfaces, which conflicts with the desired model where workspace coordination is local runtime state. The workspace-manager skill needs to make the in-repo workspace collection explicitly untracked while preserving per-agent Git worktrees for source mutations.

## What Changes

- **BREAKING**: Revise the in-repo workspace posture so `<repo-root>/houmao-ws` is an untracked local workspace collection, not a tracked repository workspace or Git-mergeable knowledge surface.
- Keep task-scoped in-repo workspaces under `<repo-root>/houmao-ws/<task-name>`.
- Add explicit task-local surfaces:
  - `<task-name>/shared-kb/` for cross-run shared task knowledge.
  - `<task-name>/owner-states/<subdir>/...` for per-run task-owner bookkeeping.
  - Per-agent workspace directories containing private Git worktrees for source changes and local bookkeeping areas for agent state.
- Require the workspace-manager to keep the workspace collection ignored by default, preferably through `.git/info/exclude` so setup does not mutate tracked ignore files unless requested.
- Remove guidance that shared-KB changes are intended to merge through Git; only source changes in per-agent worktrees are Git-facing by default.
- Update workspace documentation, memo seed guidance, and loop-facing summaries to describe shared visibility, private mutation surfaces, cross-run shared knowledge, and per-run owner state.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-utils-workspace-mgr-skill`: Revise in-repo workspace requirements from Git-tracked/shared-KB merge semantics to an untracked local workspace collection with task-level shared knowledge, per-run owner state, and per-agent Git worktrees.

## Impact

- Packaged `houmao-utils-workspace-mgr` skill guidance and its `subskills/in-repo-workspace.md` behavior.
- OpenSpec capability requirements for `houmao-utils-workspace-mgr-skill`.
- Tests or documentation that assert `houmao-ws` shared-KB content is a Git merge surface.
- Launch-profile memo seed text generated for in-repo workspaces.
- Workspace ignore handling, especially default use of `.git/info/exclude` for `houmao-ws/`.
