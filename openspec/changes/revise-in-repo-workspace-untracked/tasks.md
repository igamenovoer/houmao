## 1. Skill Contract Updates

- [x] 1.1 Locate the packaged `houmao-utils-workspace-mgr` asset and its in-repo subskill guidance.
- [x] 1.2 Revise in-repo guidance so `<repo-root>/houmao-ws` is an untracked local workspace collection.
- [x] 1.3 Update task-scoped layout guidance to require `<task-name>/workspace.md`, `<task-name>/shared-kb/`, `<task-name>/owner-states/`, and one per-agent workspace directory.
- [x] 1.4 Remove or replace wording that treats `shared-kb` as a Git merge surface.
- [x] 1.5 Document that source changes intended for Git belong in each agent's private worktree.

## 2. Workspace Planning And Execution Behavior

- [x] 2.1 Update plan output to report the untracked workspace collection, task root, cross-run `shared-kb/`, per-run `owner-states/<subdir>/...`, and per-agent worktree paths.
- [x] 2.2 Update execute behavior to create the revised task workspace layout.
- [x] 2.3 Ensure execute keeps `houmao-ws/` ignored by default, preferring `.git/info/exclude` unless a tracked ignore update is explicitly requested.
- [x] 2.4 Update `workspace.md` generation to record untracked local-state ownership rules, shared visibility, private source-mutation surfaces, shared task knowledge, and per-run owner-state paths.

## 3. Memo Seeds And Loop Summaries

- [x] 3.1 Update generated memo seed rules for in-repo workspaces to describe private worktrees, untracked `shared-kb/`, and per-run `owner-states/<subdir>/...`.
- [x] 3.2 Update loop-facing summaries to include the selected task name, task root, untracked workspace collection, shared knowledge surface, owner-state surface, private worktree paths, and task-qualified branch names.
- [x] 3.3 Ensure guidance marks sibling agent bookkeeping directories and worktrees read-only by default for non-owning agents.

## 4. Tests And Validation

- [x] 4.1 Add or update tests covering in-repo planning for the revised untracked task workspace layout.
- [x] 4.2 Add or update tests covering execution ignore handling for `houmao-ws/`.
- [x] 4.3 Add or update tests covering `workspace.md`, memo seed, and loop-summary text for the revised ownership model.
- [x] 4.4 Run targeted tests for workspace-manager skill behavior.
- [x] 4.5 Run `openspec validate revise-in-repo-workspace-untracked --strict`.
