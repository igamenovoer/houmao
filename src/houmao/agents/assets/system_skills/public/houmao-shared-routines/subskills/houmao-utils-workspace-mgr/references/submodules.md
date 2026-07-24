# Submodules

Tracked submodule content must be accessible inside worktrees, and agents may need to branch, commit, and push inside submodules without a fresh large checkout.

## Modes

Supported submodule materialization modes:

| Mode | Meaning |
| --- | --- |
| `seeded-worktree` | Default. Create a real Git worktree for each submodule inside the agent worktree, but seed files from the already-initialized source checkout. |
| `empty` | Leave the submodule uninitialized or empty. |
| `checkout` | Run `git submodule update --init --recursive` inside the agent worktree. |

Use `seeded-worktree` by default.

## Seeded Worktree Procedure

1. Discover tracked submodules from `.gitmodules` and the Git index.
2. Require the source checkout submodule to be initialized.
3. Get the superproject-recorded submodule commit with `git rev-parse HEAD:<submodule-path>`.
4. Run `git worktree add --no-checkout` from the source submodule repository into the agent submodule path.
5. Use an agent-owned submodule branch such as `houmao/<task-name>/<agent-name>/main` for task-scoped in-repo workspaces, or `houmao/<agent-name>/main` otherwise.
6. Seed files from the source submodule checkout while preserving the new worktree `.git` file.
7. Do not copy the source submodule `.git` file or directory.
8. Prefer reflink/copy-on-write seeding; warn before full-copy fallback for large submodules.
9. Run `git reset --mixed HEAD` inside the seeded submodule worktree.
10. Report dirty state if seeded files do not match the recorded commit.

## Integration

Agents that commit inside a submodule must also commit the updated submodule gitlink in the superproject agent branch. If the submodule has a remote, push the submodule branch before relying on the superproject gitlink update.

Agents should not add, remove, or reconfigure submodules. When integrating agent branches, prefer cherry-pick or path-limited review so intended code and gitlink updates are accepted without accidental `.gitmodules` or submodule-structure changes.

## Validation

Validation must report each tracked submodule considered, the selected materialization mode, whether the expected path is present inside the worktree, whether seeded or checkout materialization points at the expected commit, and any dirty state that could affect project commands.
