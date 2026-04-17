# Task: `houmao-utils-workspace-mgr`

Add a new system skill named `houmao-utils-workspace-mgr`. The skill helps an operator design, create, inspect, and maintain a multi-agent workspace before launching agents from a list of launch profiles.

The workspace manager should not launch agents directly. Its job is to prepare the directory layout, Git worktrees, branch names, ignore rules, and knowledge-base paths that the launch step will use as each agent's `cwd`.

## Inputs

The workspace manager is given:

- a workspace flavor: `in-repo` or `out-of-repo`
- a list of launch profiles
- for each launch profile, a stable profile name that becomes the default `agent-name`
- optional repo bindings for each agent when the workspace is `out-of-repo`
- optional per-agent cwd overrides, only when the override still points inside that agent's workspace

The skill should normalize each `agent-name` into a path-safe slug and use that slug consistently for directory names and branch names. The skill should refuse names that normalize to an empty slug or collide with another agent.

## Common Terms

- `ws-root`: root directory of the multi-agent workspace.
- `agent-name`: normalized launch profile name.
- `agent-ws`: per-agent workspace at `<ws-root>/<agent-name>`.
- `agent-repo`: per-agent Git worktree for a target repo.
- `agent-kb`: per-agent knowledge base owned by one agent.
- `shared-kb`: shared knowledge base intended for cross-agent notes.
- `workspace repo`: Git repo that tracks workspace metadata and workspace-owned knowledge, not necessarily the target code repos.
- `target repo`: code repo that agents will edit.

## Common Organization Rules

The workspace manager should keep these responsibilities separate:

- Workspace scaffolding: directories, manifests, and per-agent knowledge that belong to the workspace.
- Target repo checkouts: Git worktrees, symlinks, or copied repos used as working code trees.
- Shared standalone repos: local bare repositories used as sources for worktrees, such as `shared-kb.git`.
- Runtime state: Houmao runtime homes, logs, gateways, mailboxes, and generated provider homes remain under existing Houmao runtime/project mechanisms and should not be mixed into this workspace layout.
- Reusable local development state: selected non-AI local directories may be symlinked into target repo worktrees when doing so is safe.
- Tracked submodules: target repo submodule paths may be left empty, seeded from the source checkout as real submodule worktrees, or cleanly checked out per workspace policy.

Each `agent-ws` should be treated as one agent's home base. Other agents may read another agent's `kb` directory, but should not edit it unless the operator explicitly asks for handoff or repair.

Each agent should get a stable default branch name:

```text
houmao/<agent-name>/main
```

For multi-repo out-of-repo workspaces, the same branch name may be used in each target repo because branch namespaces are per Git repository. If the operator wants easier cross-repo visual scanning, the workspace manager may support an explicit branch template such as `houmao/<agent-name>/<repo-name>`.

## Worktree Local-State Symlink Policy

The generic `magic-context/skills/devel/create-git-worktree` workflow symlinks reusable local-state directories into a new worktree. Its default candidates are:

```text
.claude
.codex
.gemini
.github
.aider
.cursor
.continue
.windsurf
.kiro
```

and it also links `.pixi` for Pixi projects when `.pixi/` exists as an untracked local directory.

`houmao-utils-workspace-mgr` should not blindly reuse those defaults. Houmao-managed workspaces should keep AI tool state isolated per launched agent and per Houmao runtime home.

The workspace manager must not symlink these AI tool directories into Houmao agent worktrees by default:

```text
.claude
.codex
.gemini
.aider
.cursor
.continue
.windsurf
.kiro
```

Reasons:

- `.claude`, `.codex`, and `.gemini` may contain provider homes, project-local settings, credentials, session state, or trust/config files that should be owned by Houmao launch preparation.
- AI coding assistant directories such as `.aider`, `.cursor`, `.continue`, `.windsurf`, and `.kiro` may contain local agent state or project instructions that are not safe to share across agents.
- Symlinking these directories can make agents share mutable state accidentally and can let project-local AI config override launch-owned Houmao settings.

The workspace manager may support symlinking explicitly allowed non-AI local-state directories, using the same safety rules as `create-git-worktree`:

- only symlink when the source path exists in the source repo root
- skip the path if Git tracks any files under it
- do not replace tracked content in the new worktree with a symlink
- record linked and skipped directories in `workspace.md`

Default allowed candidates for Houmao usage should be conservative:

```text
.pixi
```

The workspace manager may allow `.github` only when it is untracked and the operator explicitly requests it. In most repositories `.github` is tracked project content and should come from the Git worktree itself, not from a symlink.

## Tracked Submodule Materialization Policy

Target repos may contain tracked Git submodules. A newly created Git worktree usually has the superproject gitlink entries, but submodule working trees are not initialized until `git submodule update` runs. The workspace manager should let the operator choose how submodules are materialized in each agent worktree.

Supported modes:

- `seeded-worktree` (default): create real Git worktree metadata for each submodule inside the agent worktree, but do not run a fresh submodule checkout; seed file contents from the already-initialized source checkout.
- `empty`: leave submodule paths uninitialized or empty in the agent worktree.
- `checkout`: run a clean submodule checkout in the agent worktree with `git submodule update --init --recursive`.

The default is `seeded-worktree`.

`seeded-worktree` mode is the preferred Houmao solution when submodules are too large to check out repeatedly but agents still need normal Git behavior inside submodules. It creates a real submodule worktree at the agent's submodule path, so the agent can create branches, commit normally, and push from inside the submodule. It avoids a new Git checkout of the submodule files by reusing the source checkout's existing working-tree content as the seed.

`seeded-worktree` mode rules:

- discover tracked submodule paths from the target repo's `.gitmodules` and Git index
- require the source checkout submodule path to already be initialized
- create the agent submodule path with `git worktree add --no-checkout` from the source submodule repository, using the superproject's recorded submodule commit as the start point
- create or check out an agent-owned submodule branch, such as `houmao/<agent-name>/main`, inside that submodule repository
- seed ordinary working-tree content from the source checkout into the agent submodule path while preserving the newly created `.git` file for the agent submodule worktree
- do not copy the source submodule `.git` file or `.git` directory
- prefer filesystem copy-on-write/reflink seeding when available; if reflink is unavailable, warn before falling back to a full content copy for large submodules
- after seeding, run `git reset --mixed HEAD` inside the agent submodule worktree so the index matches the branch while the seeded working tree remains in place
- if the seeded content does not match the superproject's recorded submodule commit, report the resulting dirty submodule state instead of silently forcing it clean
- do not overwrite local modifications in an existing agent submodule worktree without explicit operator confirmation
- record seeded, missing, skipped, dirty, and failed submodule paths in `workspace.md`

When an agent commits inside a submodule, the agent must also commit the updated submodule gitlink in the superproject agent branch:

```bash
git -C <agent-repo>/<submodule-path> checkout -b houmao/<agent-name>/main
git -C <agent-repo>/<submodule-path> add .
git -C <agent-repo>/<submodule-path> commit -m "..."
git -C <agent-repo>/<submodule-path> push -u origin houmao/<agent-name>/main
git -C <agent-repo> add <submodule-path>
git -C <agent-repo> commit -m "update <submodule-path>"
```

The push step applies only when the submodule has a remote or other configured publication target.

Empty mode rules:

- do not initialize submodules
- ensure the expected submodule parent directories may exist, but do not require dependency files to be present
- warn that builds or tests requiring submodule contents may fail until the operator or agent initializes them

Checkout mode rules:

- run the clean checkout from inside the agent worktree, not from the source checkout
- honor the target repo's tracked submodule commit recorded by the superproject
- use recursive checkout unless the operator requests non-recursive behavior
- if the agent needs to commit inside the submodule, create or check out an agent-owned branch inside the submodule instead of committing on the default detached HEAD
- after committing in the submodule, commit the updated submodule gitlink in the superproject agent branch
- warn before network access when submodule URLs are remote or when local file protocol policy may block local submodule URLs

If `seeded-worktree` mode cannot seed a submodule because the source checkout has not initialized it, the workspace manager should warn and leave that submodule empty unless the operator selected `checkout` or explicitly allowed fallback checkout.

Submodule structure is out of scope for agent worktrees by default. Agents should not add, remove, or reconfigure submodules. When integrating an agent branch back to the main repo, prefer cherry-picking or path-limited integration so ordinary code and intended submodule gitlink updates are brought over without accepting accidental `.gitmodules` or submodule structure changes.

## In-Repo Workspace

Use `in-repo` when the operator wants workspace notes, agent-specific knowledge, and shared knowledge to be tracked by the current repository.

The operator must run the setup from inside a Git repo. The repo top-level directory is `repo-root`, and the workspace root is:

```text
<repo-root>/houmao-ws
```

### In-Repo Directory Layout

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

The following paths should be tracked by the parent repository:

- `<repo-root>/houmao-ws/README.md`
- `<repo-root>/houmao-ws/workspace.md`
- `<repo-root>/houmao-ws/shared-kb/**`
- `<repo-root>/houmao-ws/<agent-name>/README.md`
- `<repo-root>/houmao-ws/<agent-name>/kb/**`

The following paths should be ignored by the parent repository:

```gitignore
/houmao-ws/*/repo/
```

The ignored `repo/` directory is still a real Git worktree of `repo-root`. It is ignored only from the parent checkout so the parent repo does not record it as an embedded repository.

### In-Repo Agent Worktree

For each launch profile, create:

```text
<repo-root>/houmao-ws/<agent-name>/repo
```

as a Git worktree of `repo-root` on branch:

```text
houmao/<agent-name>/main
```

The agent should normally launch with:

```text
cwd = <repo-root>/houmao-ws/<agent-name>/repo
```

This gives each agent a clean branch-local checkout of the repo. It also means the agent sees branch-local workspace knowledge at:

```text
<agent-repo>/houmao-ws/<agent-name>/kb
<agent-repo>/houmao-ws/shared-kb
```

Those branch-local paths are the preferred write targets for an agent. The sibling paths outside the worktree:

```text
<repo-root>/houmao-ws/<agent-name>/kb
<repo-root>/houmao-ws/shared-kb
```

are the operator's parent-checkout view. Agents should not write those sibling paths if their changes are intended to land on the agent branch.

When creating this worktree, apply the Worktree Local-State Symlink Policy. In particular, do not symlink `.claude`, `.codex`, `.gemini`, or other AI tool directories from `repo-root` into `agent-repo`.

Also apply the Tracked Submodule Materialization Policy for any tracked submodules in `repo-root`. The default should be `seeded-worktree`, so initialized submodule contents from the parent checkout seed real submodule worktrees inside `agent-repo` without running fresh submodule checkouts.

### In-Repo Merge Model

Agent work happens on `houmao/<agent-name>/main`. Code changes, agent KB updates, and shared KB updates all land on that branch because the agent edits them inside `agent-repo`.

To publish an agent's work, merge or cherry-pick from `houmao/<agent-name>/main` into the repo's integration branch. The merge should include:

- target code changes
- `<repo-root>/houmao-ws/<agent-name>/kb/**` updates that should be preserved
- `<repo-root>/houmao-ws/shared-kb/**` updates that should become shared knowledge

If multiple agents edit `shared-kb`, conflicts are expected. The workspace manager should document that `shared-kb` is a shared integration surface and may be curated by the operator or by a dedicated knowledge-maintainer agent.

## Out-Of-Repo Workspace

Use `out-of-repo` when the operator wants a clean multi-agent workspace outside any target repo, or when agents need to work on different target repos.

In this mode, `ws-root` is a standalone Git repo that tracks workspace metadata and workspace-owned knowledge. It does not contain target repo code as tracked files.

Typical root:

```text
<ws-root>/
```

The root should contain `.houmao/` when the workspace is also a Houmao project directory.

### Out-Of-Repo Directory Layout

```text
<ws-root>/
  .git/
  .houmao/
  .gitignore
  README.md
  workspace.md
  .shared-repos/
    shared-kb.git/          # ignored bare repo
    <local-repo-name>.git/  # optional ignored bare repo for local-only shared repos
  shared-kb/                # optional ignored operator worktree
  <agent-name>/
    README.md
    kb/
      README.md
    common-kb/              # ignored worktree of .shared-repos/shared-kb.git
    repos/
      <git-project-name>/   # ignored worktree, symlink, or copy
```

The workspace repo should track:

- `<ws-root>/README.md`
- `<ws-root>/workspace.md`
- `<ws-root>/<agent-name>/README.md`
- `<ws-root>/<agent-name>/kb/**`

The workspace repo should ignore:

```gitignore
/.shared-repos/
/shared-kb/
/*/common-kb/
/*/repos/
```

The ignored paths are independently versioned or externally owned. They should not be added to the workspace repo as embedded Git repositories.

### Out-Of-Repo Agent Workspace

Each agent gets:

```text
<ws-root>/<agent-name>
```

as its home base. The default launch cwd should be:

```text
cwd = <ws-root>/<agent-name>
```

This lets the agent see:

```text
kb/
common-kb/
repos/<git-project-name>/
```

from one stable cwd. If the operator wants an agent to focus on one repo, the launch profile may set cwd to:

```text
<ws-root>/<agent-name>/repos/<git-project-name>
```

but the workspace manager should make clear that `kb/` and `common-kb/` are then sibling paths outside the target repo checkout.

### Target Repo Bindings

Each target repo binding should declare:

- logical repo name, used as `<git-project-name>`
- source repo path or URL
- materialization mode: `worktree`, `symlink`, or `copy`
- optional branch template

The recommended materialization mode is `worktree`.

For a target repo worktree, create:

```text
<ws-root>/<agent-name>/repos/<git-project-name>
```

from the source repo on branch:

```text
houmao/<agent-name>/main
```

When creating this target repo worktree, apply the Worktree Local-State Symlink Policy. The workspace manager may link safe non-AI local state such as untracked `.pixi/`, but must not link AI tool directories such as `.claude`, `.codex`, `.gemini`, `.aider`, `.cursor`, `.continue`, `.windsurf`, or `.kiro`.

Also apply the Tracked Submodule Materialization Policy for any tracked submodules in the source repo. The default should be `seeded-worktree`, so initialized submodule contents from the source checkout seed real submodule worktrees inside the target repo worktree without running fresh submodule checkouts.

For `symlink`, create a symlink at the same path. The workspace manager should warn that all agents using the same symlink target share one working tree and can pollute each other's edits.

For `copy`, copy the source tree into the same path and initialize or preserve Git only when the operator explicitly asks for that behavior. The workspace manager should warn that copy mode consumes more disk and does not automatically share history with the source repo.

### Shared KB As A Local Standalone Repo

In `out-of-repo` mode, `shared-kb` should be a standalone local Git repo, preferably stored as a bare repo:

```text
<ws-root>/.shared-repos/shared-kb.git
```

This repo has no remote by default. It exists only inside `ws-root`.

For each agent, create a worktree:

```text
<ws-root>/<agent-name>/common-kb
```

on branch:

```text
houmao/<agent-name>/main
```

Optionally create an operator worktree:

```text
<ws-root>/shared-kb
```

on branch:

```text
main
```

This gives each agent a branch-local shared KB contribution path while keeping the shared KB history separate from the workspace repo. The operator or a dedicated knowledge-maintainer agent can merge agent KB branches into `main`.

### Local-Only Shared Repos

The same pattern can support any local-only shared repo, not just `shared-kb`:

```text
<ws-root>/.shared-repos/<local-repo-name>.git
<ws-root>/<agent-name>/repos/<local-repo-name>
```

Use a bare repo as the durable local source and create per-agent worktrees from it. The workspace repo should ignore both the bare repo and the per-agent worktrees.

This is the preferred answer for the case where the operator wants a `shared-repo` that is a real standalone Git repo, has no remote, exists only inside this workspace, and can be introduced into each agent's workspace as a Git worktree.

## Workspace Manifest

The workspace manager should maintain a human-readable manifest at:

```text
<ws-root>/workspace.md
```

The manifest should record:

- workspace flavor
- `ws-root`
- agent names and source launch profile names
- launch cwd for each agent
- target repo bindings for each agent
- branch names created for each worktree
- submodule materialization mode for each target repo worktree
- submodule paths seeded, left empty, checked out, skipped, dirty, or failed
- paths ignored from the workspace repo
- shared local repos such as `.shared-repos/shared-kb.git`

The manifest is documentation, not the only source of truth. The skill should inspect the filesystem and Git state when asked for status.

## Skill Operations

The `houmao-utils-workspace-mgr` skill should eventually support these operator tasks:

- explain the two workspace flavors and recommend one
- plan a workspace layout from launch profiles
- create `in-repo` workspace scaffolding
- create `out-of-repo` workspace scaffolding
- add one agent workspace
- add one target repo binding
- create or attach a local-only shared repo
- create per-agent worktrees
- print launch cwd values for each agent
- inspect workspace status
- warn about dirty worktrees, missing branches, missing ignored paths, and branch-name collisions
- warn about missing source submodule contents when the selected submodule mode is `seeded-worktree`
- produce cleanup instructions without deleting data by default

## Guardrails

- Do not store Houmao runtime state inside `houmao-ws/` or inside out-of-repo agent workspaces unless an existing Houmao command already chooses that path.
- Do not commit nested Git worktrees into the parent workspace repo.
- Do not silently overwrite an existing worktree, symlink, copied repo, or local bare repo.
- Do not create two worktrees that check out the same branch from the same Git repo at the same time.
- Do not point multiple agents at the same mutable submodule working tree when they are expected to commit independently.
- Do not copy submodule `.git` metadata from one checkout into another worktree.
- Do not let one agent's default writable KB path point into another agent's `kb`.
- Do not assume a local-only shared repo is portable across clones unless the operator exports it as a Git bundle or pushes it to a remote.
