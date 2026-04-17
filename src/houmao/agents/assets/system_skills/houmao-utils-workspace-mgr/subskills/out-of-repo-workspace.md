# Out-Of-Repo Workspace

Use `out-of-repo` when the operator wants a clean multi-agent workspace outside target repos, or when agents need to work on different repos.

In this mode, `ws-root` is a standalone workspace Git repo. It tracks workspace metadata and workspace-owned knowledge, not target repo code.

## Directory Layout

Create or maintain this layout:

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

Track these paths in the workspace repo:

- `<ws-root>/README.md`
- `<ws-root>/workspace.md`
- `<ws-root>/<agent-name>/README.md`
- `<ws-root>/<agent-name>/kb/**`

Ignore externally-owned or independently-versioned paths:

```gitignore
/.shared-repos/
/shared-kb/
/*/common-kb/
/*/repos/
```

## Agent Workspace

Each agent gets:

```text
<ws-root>/<agent-name>
```

Default launch cwd:

```text
<ws-root>/<agent-name>
```

This lets the agent see:

```text
kb/
common-kb/
repos/<git-project-name>/
```

from one stable cwd.

If the operator wants an agent to focus on one repo, the launch profile may use:

```text
<ws-root>/<agent-name>/repos/<git-project-name>
```

In that case, make clear in the plan and memo seed that `kb/` and `common-kb/` are sibling paths outside the focused repo checkout.

## Target Repo Bindings

Each binding should declare:

- logical repo name, used as `<git-project-name>`
- source repo path or URL
- materialization mode: `worktree`, `symlink`, or `copy`
- optional branch template

Recommended materialization mode: `worktree`.

For a target repo worktree, create:

```text
<ws-root>/<agent-name>/repos/<git-project-name>
```

from the source repo on branch:

```text
houmao/<agent-name>/main
```

Apply the shared local-state symlink and tracked-submodule policies from `SKILL.md`.

For `symlink`, create a symlink at the same path and warn that agents using the same symlink target share one mutable working tree.

For `copy`, copy the source tree into the same path and initialize or preserve Git only when the operator explicitly asks for that behavior. Warn that copy mode consumes more disk and does not automatically share history with the source repo.

## Shared KB And Local Shared Repos

For shared KB, create a local bare repo:

```text
<ws-root>/.shared-repos/shared-kb.git
```

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

The same pattern supports any local-only shared repo:

```text
<ws-root>/.shared-repos/<local-repo-name>.git
<ws-root>/<agent-name>/repos/<local-repo-name>
```

Use a bare repo as the durable local source and per-agent worktrees as writable views. Ignore both the bare repo and per-agent worktrees from the workspace repo.

Local-only shared repos are not portable across clones unless exported as a Git bundle or pushed to a remote.

## Plan Requirements

For `plan`, include:

- resolved `ws-root`
- whether `ws-root` exists and whether it is already a Git repo
- every agent workspace path
- every target repo binding and materialization decision
- every local-only shared repo and per-agent worktree
- workspace `.gitignore` additions
- submodule decisions for each bound target repo
- local-state symlink decisions for each target repo worktree
- launch-profile cwd changes
- optional memo-seed file paths

## Execute Steps

For `execute`:

1. Create or validate `ws-root` as a Git repo.
2. Create `.houmao/` only when the workspace is also intended to be a Houmao project directory.
3. Create tracked workspace metadata and per-agent KB directories.
4. Add ignore rules for `.shared-repos/`, `shared-kb/`, `*/common-kb/`, and `*/repos/`.
5. Create or attach local-only shared bare repos.
6. Create per-agent `common-kb` worktrees.
7. Materialize target repo bindings under each `repos/` path.
8. Apply the shared local-state symlink policy from `SKILL.md`.
9. Apply the shared tracked-submodule policy from `SKILL.md`.
10. Write or update `<ws-root>/workspace.md`.
11. Update launch profiles to the planned cwd values.
12. Optionally create per-agent memo seed Markdown and attach it to profiles.

Do not launch agents from this skill.
