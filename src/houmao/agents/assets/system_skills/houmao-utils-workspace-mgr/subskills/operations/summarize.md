# Summarize Operation

Use `summarize` when the user wants compact facts about a planned or prepared workspace.

The summary is consumer-neutral. It may be used by humans, scripts, or upstream planners, but this skill does not make any caller type part of its own contract.

## Read First

- Selected flavor page when flavor is known:
  - [../in-repo-workspace.md](../in-repo-workspace.md)
  - [../out-of-repo-workspace.md](../out-of-repo-workspace.md)
- [../reference/workspace-contract.md](../reference/workspace-contract.md)

## Summary Fields

For each prepared workspace, identify:

- selected workspace flavor
- workspace root and task root when applicable
- selected `task-name` for `in-repo`
- launch cwd or shared visibility surface
- private source-mutation surface
- shared writable surfaces
- default read-only shared surfaces
- local-state link posture
- validation posture when validation has run
- ad hoc worktree posture
- branch names
- relevant `workspace.md` path

For in-repo mode, include `<repo-root>/houmao-ws` as the untracked workspace collection, `<task-root>/shared-kb/` as cross-run shared task knowledge, `<task-root>/owner-states/<subdir>/...` as per-run task-owner bookkeeping when selected, and each agent's private `repo/` worktree.

## Output

Prefer a concise Markdown table plus short notes for risks or missing validation.
