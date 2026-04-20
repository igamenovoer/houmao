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

## Agent Cwd And Worktree

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
<repo-root>
```

The repo root is the shared visibility surface. Agents launch from `<repo-root>` so they can inspect the parent checkout, `workspace.md`, every agent KB, and every agent worktree from one stable location.

The per-agent `repo/` worktree is the safe mutation surface for source changes and shared-KB changes that should merge through Git. Inside the worktree, branch-local workspace knowledge is available at:

```text
<agent-repo>/houmao-ws/<agent-name>/kb
<agent-repo>/houmao-ws/shared-kb
```

The sibling paths outside the worktree:

```text
<repo-root>/houmao-ws/<agent-name>/kb
<repo-root>/houmao-ws/shared-kb
```

are the parent-checkout view. Agent-specific KB in the parent checkout is the direct note-sharing surface: the owning agent may write its own `kb/` directory, and peers may read it. Shared-KB changes that should merge through Git should be made in the owning agent's private worktree copy, not in the parent-checkout `shared-kb/`.

## In-Repo Write Ownership

Use this default read/write contract for in-repo workspaces:

| Path | Owning agent may read | Owning agent may write | Other agents may read | Other agents may write | Purpose |
| --- | --- | --- | --- | --- | --- |
| `<repo-root>/<project-path>` | yes | no by default | yes | no by default | Parent source checkout and shared visibility surface. |
| `<repo-root>/houmao-ws/<agent-name>/repo/<project-path>` | yes | yes | yes | no by default | Private branch worktree for source changes. |
| `<repo-root>/houmao-ws/<agent-name>/repo/houmao-ws/shared-kb/**` | yes | yes | yes | no by default | Private branch copy for shared-KB changes intended to merge through Git. |
| `<repo-root>/houmao-ws/shared-kb/**` | yes | no by default | yes | no by default | Parent-checkout shared-KB view. |
| `<repo-root>/houmao-ws/<agent-name>/kb/**` | yes | yes | yes | no | Agent-owned notes visible to peers. |
| `<repo-root>/houmao-ws/<other-agent>/kb/**` | yes | no | yes | owner only | Sibling agent notes. |
| `<repo-root>/houmao-ws/<other-agent>/repo/**` | yes | no | yes | owner only | Sibling private worktree. |
| `<repo-root>/houmao-ws/workspace.md` | yes | no by default | yes | no by default | Operator and workspace-manager contract. |

If an agent needs to change source or shared KB, it should edit under its own `repo/` worktree. If an agent needs to communicate directly, it should write under its own parent-checkout `kb/` path. Do not use another agent's worktree or KB as scratch space.

## Plan Requirements

For `plan`, include:

- resolved `repo-root` and `ws-root`
- every agent directory under `houmao-ws/`
- every agent worktree path and branch
- default launch cwd as `<repo-root>`
- shared visibility surface and safe write targets
- in-repo read/write ownership rules
- parent-repo `.gitignore` additions
- private worktree source and shared-KB paths agents should write
- parent-checkout agent KB paths each owning agent may write
- submodule materialization decisions for `repo-root`
- recursive local-state symlink decisions for each agent worktree, including reachable `.pixi/`, non-hidden local-only paths, hidden-path skips, symlink traversal skips, and tracked-content conflict skips
- launch-profile cwd changes
- optional memo-seed file paths

## Execute Steps

For `execute`:

1. Verify `repo-root` is a Git repo.
2. Create `houmao-ws/`, shared KB, per-agent KB, and per-agent README files as needed.
3. Add `/houmao-ws/*/repo/` to the parent repo ignore rules if missing.
4. Create one Git worktree per agent at `<ws-root>/<agent-name>/repo`.
5. Apply the shared local-state symlink policy from `SKILL.md`, preserving relative paths for linked local-only state.
6. Apply the shared tracked-submodule policy from `SKILL.md`.
7. Write or update `<ws-root>/workspace.md`, including the repo-root cwd, shared visibility surface, and in-repo read/write ownership rules.
8. Update launch profiles so each agent cwd points at `<repo-root>`.
9. Optionally create per-agent memo seed Markdown and attach it to profiles.

Do not launch agents from this skill.

## Merge Model

Source work happens on `houmao/<agent-name>/main` because the agent edits source files inside its private `repo/` worktree. Shared-KB changes intended for Git merge also happen on that branch when the agent edits `houmao-ws/shared-kb/**` inside its private worktree.

Agent-specific parent-checkout KB updates under `houmao-ws/<agent-name>/kb/**` are direct owner notes, not private worktree source changes. If those notes should be committed, prefer operator-curated commits or narrow pathspec commits for the owning agent's KB path.

To publish an agent's work, merge or cherry-pick from the agent branch into the repo's integration branch. Include intended updates to:

- target code
- `houmao-ws/shared-kb/**`
- submodule gitlinks that correspond to pushed submodule commits

If multiple agents edit `shared-kb`, conflicts are expected. Treat `shared-kb` as an integration surface that may be curated by the operator or a dedicated knowledge-maintainer agent.

Avoid accepting accidental `.gitmodules` or submodule add/delete changes during integration.
