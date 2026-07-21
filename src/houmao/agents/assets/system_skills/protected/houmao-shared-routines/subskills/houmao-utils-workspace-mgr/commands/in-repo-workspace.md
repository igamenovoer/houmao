# In-Repo Workspace

Use `in-repo` when the operator wants a task-scoped local workspace collection under the current repository. The collection is convenient to inspect from the repo root, but it is workspace runtime state and is not meant to be tracked by the parent repository.

Require the setup command to run from inside a Git repo. Resolve the repo top-level directory as `repo-root`.

Resolve one `task-name` for the workspace team. If the task name cannot be inferred safely, ask with `Required: task-name` and an `Optional` section for workspace root, branch naming preference, owner-state subdir, or `none for this step`; do not invent one.

Default workspace collection root:

```text
<repo-root>/houmao-ws
```

Task root:

```text
<repo-root>/houmao-ws/<task-name>
```

## Directory Layout

Create this layout:

```text
<repo-root>/
  houmao-ws/                 # untracked local workspace collection
    workspaces.md            # optional local index across task workspaces
    <task-name>/
      workspace.md           # task-local operating contract
      shared-kb/             # untracked cross-run task knowledge
        README.md
      owner-states/          # untracked per-run task-owner bookkeeping
        <subdir>/
      <agent-name>/
        README.md
        states/              # untracked agent-local bookkeeping
        repo/                # ignored Git worktree of <repo-root>
```

Operators, scripts, or upstream plans may request additional task-scoped bookkeeping directories while still using this standard in-repo flavor. Keep the base layout above authoritative, then add only the requested local-state paths. Put task-owner run records under:

```text
<repo-root>/houmao-ws/<task-name>/owner-states/<subdir>/...
```

The `owner-states/<subdir>` name may come from a run id, operator label, or upstream state directory. Record the selected subdir in the plan and `workspace.md`; do not impose a fixed subtree below it unless the workspace requirements ask for one.

Treat `shared-kb/` as task knowledge that may persist across multiple runs. Treat `owner-states/<subdir>/...` as per-run task-owner bookkeeping. Treat each agent's `states/` directory as local agent-owned bookkeeping unless the task contract assigns narrower ownership.

The entire in-repo workspace collection is untracked local state. Keep it out of the parent repository's tracked file set by default with a local ignore rule:

```gitignore
/houmao-ws/
```

Prefer writing that rule to `.git/info/exclude`. Mutate tracked ignore files only when the operator explicitly requests a repository-wide ignore rule.

The ignored `repo/` directory is still a real Git worktree of `repo-root`; it is ignored only so the parent checkout does not record it as an embedded repository.

## Agent Cwd And Worktree

For each launch profile, create:

```text
<repo-root>/houmao-ws/<task-name>/<agent-name>/repo
```

as a Git worktree of `repo-root` on branch:

```text
houmao/<task-name>/<agent-name>/main
```

Default launch cwd:

```text
<repo-root>
```

The repo root is the shared visibility surface. Agents launch from `<repo-root>` so they can inspect the parent checkout, the local `houmao-ws/workspaces.md` index, task-local `workspace.md`, task shared knowledge, owner-state records, and task worktrees from one stable location.

The per-agent `repo/` worktree is the safe mutation surface for source changes and submodule gitlink changes intended to merge through Git.

The workspace-local paths:

```text
<repo-root>/houmao-ws/<task-name>/shared-kb
<repo-root>/houmao-ws/<task-name>/owner-states/<subdir>
<repo-root>/houmao-ws/<task-name>/<agent-name>/states
```

are untracked local coordination surfaces. Do not tell agents to commit or merge these paths through the parent repository. If shared task knowledge must leave the machine, the operator should export, copy, or otherwise publish it deliberately.

## In-Repo Write Ownership

Use this default read/write contract for task-scoped in-repo workspaces:

| Path | Owning agent may read | Owning agent may write | Other agents may read | Other agents may write | Purpose |
| --- | --- | --- | --- | --- | --- |
| `<repo-root>/<project-path>` | yes | no by default | yes | no by default | Parent source checkout and shared visibility surface. |
| `<repo-root>/houmao-ws/<task-name>/<agent-name>/repo/<project-path>` | yes | yes | yes | no by default | Private branch worktree for source changes. |
| `<repo-root>/houmao-ws/<task-name>/shared-kb/**` | yes | yes when assigned | yes | yes when assigned | Untracked cross-run shared task knowledge. |
| `<repo-root>/houmao-ws/<task-name>/owner-states/<subdir>/**` | yes | task owner only by default | yes | no by default | Untracked per-run task-owner bookkeeping. |
| `<repo-root>/houmao-ws/<task-name>/<agent-name>/states/**` | yes | yes | yes | no | Agent-owned local bookkeeping. |
| `<repo-root>/houmao-ws/<task-name>/<other-agent>/states/**` | yes | no | yes | owner only | Sibling agent bookkeeping inside the same task. |
| `<repo-root>/houmao-ws/<task-name>/<other-agent>/repo/**` | yes | no | yes | owner only | Sibling private worktree inside the same task. |
| `<repo-root>/houmao-ws/<task-name>/workspace.md` | yes | no by default | yes | no by default | Task-local workspace-manager contract. |
| `<repo-root>/houmao-ws/workspaces.md` | yes | no by default | yes | no by default | Local repo-level workspace index. |

If an agent needs to change source, it should edit under its own `repo/` worktree. If an agent needs to record private or owner-local coordination notes, it should write under its own `states/` path or another path explicitly assigned by the task contract. Do not use another agent's worktree or bookkeeping directory as scratch space.

## Plan Requirements

For `plan`, include:

- resolved `repo-root`, `ws-root`, `task-name`, and `task-root`
- that `ws-root` is an untracked local workspace collection
- planned `.git/info/exclude` or explicit tracked ignore-file handling for `/houmao-ws/`
- local `houmao-ws/workspaces.md` index behavior
- every agent directory under `houmao-ws/<task-name>/`
- every agent worktree path and task-qualified branch
- default launch cwd as `<repo-root>`
- shared visibility surface and safe write targets
- task-local `shared-kb/` as cross-run shared task knowledge
- task-local `owner-states/<subdir>/...` as per-run task-owner bookkeeping when an owner-state subdir is selected
- agent-local bookkeeping surfaces
- in-repo read/write ownership rules
- private worktree source paths agents should write
- submodule materialization decisions for `repo-root`
- recursive local-state symlink decisions for each agent worktree, including reachable `.pixi/`, non-hidden local-only paths, hidden-path skips, symlink traversal skips, and tracked-content conflict skips
- launch-profile cwd changes
- optional memo-seed file paths

## Create Steps

For `create`:

1. Verify `repo-root` is a Git repo.
2. Create `houmao-ws/`, local `workspaces.md`, task-local `workspace.md`, task-local `shared-kb/`, task-local `owner-states/`, per-agent `states/`, and any requested `owner-states/<subdir>/...` directories as needed.
3. Ensure `/houmao-ws/` is ignored from the parent repo, preferring `.git/info/exclude` unless the operator explicitly requests a tracked ignore-file update.
4. Create one Git worktree per agent at `<task-root>/<agent-name>/repo`.
5. Apply the shared local-state symlink policy from [reference/local-state-links.md](../references/local-state-links.md), preserving relative paths for linked local-only state.
6. Apply the shared tracked-submodule policy from [reference/submodules.md](../references/submodules.md).
7. Write or update `<task-root>/workspace.md` plus the local `houmao-ws/workspaces.md`, including the repo-root cwd, shared visibility surface, task-local contract, untracked workspace collection, ignore decision, shared knowledge path, owner-state path, and in-repo read/write ownership rules.
8. Update launch profiles so each agent cwd points at `<repo-root>`.
9. Optionally create per-agent memo seed Markdown and attach it to profiles.

Do not launch agents from this skill.

## Integration Model

Source work happens on `houmao/<task-name>/<agent-name>/main` because the agent edits source files inside its private `repo/` worktree.

Task-local `shared-kb/`, task-local `owner-states/<subdir>/...`, and agent-local `states/` are untracked coordination surfaces. They are not Git merge surfaces. If an operator wants durable repository documentation from those surfaces, the operator should intentionally copy or curate that material into tracked project files.

To publish an agent's source work, merge or cherry-pick from the agent branch into the repo's integration branch. Include intended source updates and submodule gitlinks that correspond to pushed submodule commits.

Avoid accepting accidental `.gitmodules` or submodule add/delete changes during integration.
