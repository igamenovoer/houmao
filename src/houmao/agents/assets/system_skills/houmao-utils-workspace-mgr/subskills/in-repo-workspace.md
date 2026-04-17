# In-Repo Workspace

Use `in-repo` when the operator wants workspace notes, per-agent knowledge, and shared knowledge tracked by the current repository.

Require the setup command to run from inside a Git repo. Resolve the repo top-level directory as `repo-root`.

Default workspace root:

```text
<repo-root>/houmao-ws
```

## Directory Layout

Create this layout:

```text
<repo-root>/
  houmao-ws/
    README.md
    workspace.md
    shared-kb/
      README.md
    <agent-name>/
      README.md
      kb/
        README.md
      repo/                 # ignored Git worktree of <repo-root>
```

Track these paths in the parent repo:

- `<repo-root>/houmao-ws/README.md`
- `<repo-root>/houmao-ws/workspace.md`
- `<repo-root>/houmao-ws/shared-kb/**`
- `<repo-root>/houmao-ws/<agent-name>/README.md`
- `<repo-root>/houmao-ws/<agent-name>/kb/**`

Ignore each agent repo worktree from the parent checkout:

```gitignore
/houmao-ws/*/repo/
```

The ignored `repo/` directory is still a real Git worktree of `repo-root`; it is ignored only so the parent checkout does not record it as an embedded repository.

## Agent Worktree

For each launch profile, create:

```text
<repo-root>/houmao-ws/<agent-name>/repo
```

as a Git worktree of `repo-root` on branch:

```text
houmao/<agent-name>/main
```

Default launch cwd:

```text
<repo-root>/houmao-ws/<agent-name>/repo
```

Inside the worktree, the agent sees branch-local workspace knowledge at:

```text
<agent-repo>/houmao-ws/<agent-name>/kb
<agent-repo>/houmao-ws/shared-kb
```

Those branch-local paths are the preferred write targets for the agent. The sibling paths outside the worktree:

```text
<repo-root>/houmao-ws/<agent-name>/kb
<repo-root>/houmao-ws/shared-kb
```

are the operator's parent-checkout view. Agents should not write those sibling paths if their changes are intended to land on the agent branch.

## Plan Requirements

For `plan`, include:

- resolved `repo-root` and `ws-root`
- every agent directory under `houmao-ws/`
- every agent worktree path and branch
- parent-repo `.gitignore` additions
- branch-local KB paths agents should write
- submodule materialization decisions for `repo-root`
- local-state symlink decisions for each agent worktree
- launch-profile cwd changes
- optional memo-seed file paths

## Execute Steps

For `execute`:

1. Verify `repo-root` is a Git repo.
2. Create `houmao-ws/`, shared KB, per-agent KB, and per-agent README files as needed.
3. Add `/houmao-ws/*/repo/` to the parent repo ignore rules if missing.
4. Create one Git worktree per agent at `<ws-root>/<agent-name>/repo`.
5. Apply the shared local-state symlink policy from `SKILL.md`.
6. Apply the shared tracked-submodule policy from `SKILL.md`.
7. Write or update `<ws-root>/workspace.md`.
8. Update launch profiles so each agent cwd points at its `repo/` worktree.
9. Optionally create per-agent memo seed Markdown and attach it to profiles.

Do not launch agents from this skill.

## Merge Model

Agent work happens on `houmao/<agent-name>/main`. Code changes, agent KB updates, and shared KB updates all land on that branch because the agent edits inside `agent-repo`.

To publish an agent's work, merge or cherry-pick from the agent branch into the repo's integration branch. Include intended updates to:

- target code
- `houmao-ws/<agent-name>/kb/**`
- `houmao-ws/shared-kb/**`
- submodule gitlinks that correspond to pushed submodule commits

If multiple agents edit `shared-kb`, conflicts are expected. Treat `shared-kb` as an integration surface that may be curated by the operator or a dedicated knowledge-maintainer agent.

Avoid accepting accidental `.gitmodules` or submodule add/delete changes during integration.
