# Create Operation

Use `create` when the user explicitly asks to create or update a Houmao-standard workspace.

`execute` is a compatibility alias for `create`; do not maintain a separate behavior path for it.

## Read First

- Selected flavor page:
  - [../in-repo-workspace.md](../in-repo-workspace.md)
  - [../out-of-repo-workspace.md](../out-of-repo-workspace.md)
- [../reference/local-state-links.md](../reference/local-state-links.md)
- [../reference/submodules.md](../reference/submodules.md)
- [../reference/workspace-contract.md](../reference/workspace-contract.md)
- [../reference/memo-seeds.md](../reference/memo-seeds.md) when memo seed creation is requested

## Preconditions

- Create or reuse a current plan.
- If the user has not approved a current plan in the conversation or pointed to a plan file, summarize the plan and ask for confirmation unless the prompt explicitly requests creation now.
- Verify no target worktree, symlink, copied repo, local bare repo, or memo seed file would be overwritten without explicit confirmation.

## Create Order

1. Create workspace scaffolding, requested bookkeeping directories, and ignore rules.
2. Create or attach local-only shared repos.
3. Create per-agent superproject worktrees and branches.
4. Apply local-state link decisions so required project-local state is reachable in the worktrees.
5. Materialize tracked submodules.
6. Create knowledge and state paths.
7. Update or create flavor-specific workspace contract docs and workspace summaries.
8. Adjust launch profiles to point at prepared flavor-specific cwd values when requested.
9. Optionally create memo seed Markdown files and seed them into launch profiles.
10. Inspect final Git/filesystem status and report commands run plus remaining manual work.

Use `git worktree add` for worktrees. Do not copy a target repo manually when the selected mode is `worktree`.

## Output

Report:

- workspace root and task root when applicable
- every created or reused worktree
- every local-state link created or skipped
- every submodule materialization decision
- workspace docs written
- launch-profile cwd changes
- memo seed files created
- recommended `validate` command or validation plan
