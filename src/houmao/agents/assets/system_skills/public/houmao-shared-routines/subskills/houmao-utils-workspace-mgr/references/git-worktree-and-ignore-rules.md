# Shared Git Worktree, Ignore, and Local Shared-Repo Rules

Both `in-repo` and `out-of-repo` workspaces enforce these common Git safety and materialization invariants:

1. **Single-branch checkout isolation**: normalize each profile into a unique path-safe `<agent-name>` and never check out the same branch in more than one worktree of the same Git repository (`houmao/<task-name>/<agent-name>/main` for `in-repo`; `houmao/<agent-name>/main` or repo-qualified `houmao/<agent-name>/<repo-name>` for `out-of-repo`).
2. **Untracked nested worktrees**: keep nested worktrees and coordination directories out of parent Git tracking:
   - `in-repo`: add `/houmao-ws/` to `.git/info/exclude` by default (edit tracked `.gitignore` only when the operator explicitly requests a repository-wide rule).
   - `out-of-repo`: add `/.shared-repos/`, `/shared-kb/`, `/*/common-kb/`, and `/*/repos/` to `<ws-root>/.gitignore`.
3. **Local-state symlinks and submodules**: apply [local-state-links.md](local-state-links.md) (preserving relative paths for `.pixi/` and non-hidden local-only state while skipping AI-tool homes and tracked conflicts) and [submodules.md](submodules.md) (never sharing one mutable submodule checkout across agents that commit independently, and never copying submodule `.git` metadata across worktrees).
4. **Local bare shared repos (`.shared-repos/*.git`)**: use a local bare repo (such as `.shared-repos/shared-kb.git`) as the durable local origin and per-agent worktrees (`<agent-name>/common-kb`) as isolated writable views; warn that local bare repos are not portable across machines unless exported as a Git bundle or pushed to a remote.
5. **`--executor` and DSH Web (`--mode web`) workdir alignment**: run Git/filesystem creation and validation in the target `--executor` context when one is selected, and record whether each profile's `--workdir` targets the shared visibility root (`<repo-root>` / `<ws-root>/<agent-name>`) or a focused repo worktree (noting that DSH Web binds its browser workspace root to `--workdir`).
