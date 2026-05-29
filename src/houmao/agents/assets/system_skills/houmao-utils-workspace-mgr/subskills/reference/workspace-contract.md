# Workspace Contract And Summary

Maintain flavor-specific human-readable workspace contract docs when creating workspaces.

## Workspace Docs

Record:

- workspace flavor and root
- agents, source profiles, cwd values, and branches
- repo bindings and materialization modes
- visibility surfaces and safe write targets
- cross-run shared knowledge surfaces and per-run owner-state paths
- local-state link decisions
- submodule materialization decisions and status
- shared local repos
- ignored paths
- memo seed files created
- integration and ownership rules

For `out-of-repo`, maintain `<ws-root>/workspace.md` as the authoritative workspace contract.

For `in-repo`, maintain:

- `<repo-root>/houmao-ws/workspaces.md` as the local repo-level index across task workspaces
- `<repo-root>/houmao-ws/<task-name>/workspace.md` as the authoritative task-local workspace contract

For `in-repo`, record `<repo-root>` as the shared visibility surface, `<repo-root>/houmao-ws` as an untracked local workspace collection, the ignore rule used to keep it out of the parent repository's tracked file set, and read/write ownership for parent-checkout source paths, each agent's private worktree, task-local `shared-kb/`, task-local `owner-states/<subdir>/...`, each agent's local bookkeeping surface, sibling bookkeeping directories, sibling worktrees, task-local `workspace.md`, and repo-level `workspaces.md`.

Treat workspace docs as documentation, not as the only source of truth. Inspect Git and the filesystem for status.

## Workspace Summaries

Workspace summaries are consumer-neutral. For each agent, identify:

- selected workspace flavor
- selected `task-name` and task root for `in-repo`
- shared visibility surface or launch cwd
- private source-mutation surface
- shared writable surfaces when applicable
- default read-only shared surfaces
- local-state link posture
- validation posture when validation has run
- ad hoc worktree posture
- task-qualified branch names when applicable
- relevant `workspace.md` reference when one exists

For `in-repo`, the summary must name `<repo-root>/houmao-ws` as the untracked workspace collection, `<repo-root>/houmao-ws/<task-name>/shared-kb/` as cross-run shared task knowledge, `<repo-root>/houmao-ws/<task-name>/owner-states/<subdir>/...` as per-run task-owner bookkeeping when selected, each agent's private `repo/` worktree, and sibling bookkeeping directories and worktrees as read-only by default for non-owning agents.
