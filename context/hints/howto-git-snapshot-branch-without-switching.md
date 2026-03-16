# How to create a git snapshot branch without switching branches

When multiple processes work on the same repository simultaneously, `git checkout` is unsafe — it modifies HEAD and the working tree, which can disrupt other processes. This guide shows how to commit all current changes (including untracked files) to a throwaway branch without touching the working tree, index, or HEAD.

## Core technique: temporary index + plumbing commands

Git provides three standard plumbing commands that together allow branch creation without any checkout:

- `GIT_INDEX_FILE` — official git env var to specify an alternate index file, leaving `.git/index` untouched
- `git write-tree` — writes the current index state as a tree object
- `git commit-tree` — creates a commit object from a tree, without touching any branch
- `git branch` / `git update-ref` — creates or updates a branch ref to point to a commit

```bash
# Stage everything (tracked + untracked) into a temporary index
GIT_INDEX_FILE=/tmp/snap-index git add -A

# Write the temp index to a tree object
TREE=$(GIT_INDEX_FILE=/tmp/snap-index git write-tree)

# Create a commit object with HEAD as parent
COMMIT=$(git commit-tree "$TREE" -p HEAD -m "snapshot $(date +%Y%m%d-%H%M%S)")

# Point a new branch at that commit — no checkout
git branch snapshot-20260316 "$COMMIT"

# Clean up temp index
rm /tmp/snap-index
```

Nothing above modifies `.git/index`, the working tree, or HEAD. Other processes continue uninterrupted.

## Comparing against the snapshot later

```bash
# Diff current working tree against snapshot
git diff snapshot-20260316

# Diff only a specific path
git diff snapshot-20260316 -- src/

# See what files changed
git diff --name-status snapshot-20260316
```

## Cleaning up

```bash
git branch -D snapshot-20260316
```

## Why not `git stash create`?

`git stash create` is also non-invasive (does not touch working tree or index), but it only captures **tracked** files. The `GIT_INDEX_FILE` approach captures untracked files too via `git add -A`.

| | `git stash create` | temp index + branch |
|---|---|---|
| Touches working tree | No | No |
| Touches `.git/index` | No | No |
| Moves HEAD | No | No |
| Captures untracked files | No (unless `-u`) | Yes |
| GC risk (dangling object) | Yes (unless tagged) | No (branch ref keeps it alive) |

If untracked files don't matter, `git stash create` is simpler. Use the plumbing approach when you need a full snapshot.

## References

- [git(1) — Environment Variables (`GIT_INDEX_FILE`)](https://git-scm.com/docs/git#Documentation/git.txt-codeGITINDEXFILEcode)
- [Git Internals — Environment Variables](https://git-scm.com/book/en/v2/Git-Internals-Environment-Variables)
- [git-write-tree documentation](https://git-scm.com/docs/git-write-tree)
- [git-commit-tree documentation](https://git-scm.com/docs/git-commit-tree)
- [Git Internals — Git Objects](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects)
- [git-snap — a tool implementing this pattern](https://github.com/meribold/git-snap)
