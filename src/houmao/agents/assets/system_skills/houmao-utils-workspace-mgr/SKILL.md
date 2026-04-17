---
name: houmao-utils-workspace-mgr
description: Use Houmao's multi-agent workspace manager skill to plan or execute workspace layouts for several launch profiles, including in-repo and out-of-repo agent workspaces, Git worktrees, local-only shared repos, shared and per-agent knowledge directories, safe local-state symlinks, tracked submodule materialization, launch-profile cwd updates, and optional memo-seed augmentation with workspace rules. Use when the user asks to create, prepare, organize, inspect, dry-run, or execute a Houmao multi-agent workspace before launching agents.
---

# Houmao Workspace Manager

Use this skill to prepare multi-agent workspaces. It has two modes:

- `plan`: inspect context and show exactly what would be created or changed. Do not modify files unless the user explicitly asks to write the plan to a Markdown path.
- `execute`: create the workspace, Git worktrees, local shared repos, ignore rules, optional memo seed files, and launch-profile adjustments.

Do not launch agents from this skill. Hand off to `houmao-agent-instance` or `houmao-specialist-mgr` after workspace preparation.

## Inputs

Recover these from the prompt, current repo, launch profiles, and local Git state before asking questions:

- operation: `plan` or `execute`
- workspace flavor: `in-repo` or `out-of-repo`
- launch profiles and their stable names
- `ws-root`; default `<repo-root>/houmao-ws` for `in-repo`
- target repo bindings for `out-of-repo`
- submodule materialization choices
- local-state symlink choices
- whether to write a plan Markdown file
- whether to adjust launch profiles during `execute`
- whether to create memo-seed Markdown and merge workspace rules into profile memo seeds

If the operation is unclear, default to `plan`. If a needed value cannot be inferred safely, make a conservative decision in the plan and label it as a decision, not as a hidden assumption.

## Plan Mode

`plan` is a dry run. It must show the user the planned organization before anything is created.

Before drafting the plan, choose the workspace flavor and read the matching page from `subskills/`.

Build a plan with these sections:

1. Scope: operation, flavor, `ws-root`, source repo roots, launch profiles.
2. Directory layout: per-agent paths, repo paths, KB paths, shared repo paths.
3. Git actions: worktrees, branches, local bare repos, ignored paths.
4. Local-state symlinks: every candidate considered, selected decision, and reason.
5. Submodules: every tracked submodule considered, selected mode, and reason.
6. Launch-profile changes: cwd updates and optional memo-seed file updates.
7. Integration rules: branch naming, submodule commit rules, merge/cherry-pick guidance.
8. Risks and unresolved questions.

If the user provides a plan output path, write the plan as Markdown there. Otherwise, print the plan in the response. Writing a plan file is the only file modification allowed in `plan`.

## Execute Mode

Before changing files, create or reuse a plan. If the user has not approved a current plan in the conversation or pointed to a plan file, summarize the plan and ask for confirmation unless the prompt explicitly requests execution now.

Before executing, read the matching flavor page from `subskills/` and follow its flavor-specific execution steps.

Execute in this order:

1. Create workspace scaffolding and `.gitignore` rules.
2. Create or attach local-only shared repos.
3. Create per-agent superproject worktrees and branches.
4. Apply safe local-state symlinks.
5. Materialize tracked submodules.
6. Create per-agent KB and shared KB paths.
7. Update or create `workspace.md`.
8. Adjust launch profiles to point at the prepared cwd values.
9. Optionally create memo-seed Markdown files and seed them into launch profiles.
10. Inspect final Git/filesystem status and report commands run plus remaining manual work.

Use `git worktree add` for worktrees. Do not copy a target repo manually when the selected mode is `worktree`.

## Workspace Flavors

Load exactly one flavor page after choosing the workspace flavor:

- `subskills/in-repo-workspace.md` for workspaces rooted under the current repo.
- `subskills/out-of-repo-workspace.md` for standalone workspace repos that mount one or more target repos.

Use the selected subskill page for directory layout, flavor-specific plan contents, execution steps, and flavor-specific `workspace.md` entries. Keep using this `SKILL.md` for shared policies such as naming, local-state symlinks, submodules, launch profiles, memo seeds, and guardrails.

## Naming

Normalize each launch profile name into a path-safe `agent-name`. Refuse empty names and collisions.

Default branch:

```text
houmao/<agent-name>/main
```

For multi-repo workspaces, the same branch name may be reused in different repos. If the user asks for repo-qualified names, use `houmao/<agent-name>/<repo-name>`.

## Local-State Symlinks

Do not blindly reuse generic worktree symlink defaults.

Never symlink these AI tool directories into Houmao agent worktrees by default:

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

These can contain provider homes, credentials, trust state, local agent state, or project config that can override Houmao launch-owned settings.

Default allowed local-state symlink candidate:

```text
.pixi
```

Allow `.github` only when it is untracked and the user explicitly requests it. In most repos `.github` is tracked project content and should come from Git.

For every candidate, apply these rules:

- symlink only if the source exists
- skip if Git tracks any files under it
- do not replace tracked content in the worktree
- record linked and skipped paths in `workspace.md`

## Submodules

Tracked submodule content must be accessible inside worktrees, and agents may need to branch, commit, and push inside submodules without a fresh large checkout.

Supported submodule modes:

- `seeded-worktree` default: create a real Git worktree for each submodule inside the agent worktree, but seed files from the already-initialized source checkout.
- `empty`: leave the submodule uninitialized or empty.
- `checkout`: run `git submodule update --init --recursive` inside the agent worktree.

Use `seeded-worktree` by default.

Seeded worktree procedure:

1. Discover tracked submodules from `.gitmodules` and the Git index.
2. Require the source checkout submodule to be initialized.
3. Get the superproject-recorded submodule commit with `git rev-parse HEAD:<submodule-path>`.
4. Run `git worktree add --no-checkout` from the source submodule repository into the agent submodule path.
5. Use an agent-owned submodule branch such as `houmao/<agent-name>/main`.
6. Seed files from the source submodule checkout while preserving the new worktree `.git` file.
7. Do not copy the source submodule `.git` file or directory.
8. Prefer reflink/copy-on-write seeding; warn before full-copy fallback for large submodules.
9. Run `git reset --mixed HEAD` inside the seeded submodule worktree.
10. Report dirty state if seeded files do not match the recorded commit.

Agents that commit inside a submodule must also commit the updated submodule gitlink in the superproject agent branch. If the submodule has a remote, push the submodule branch before relying on the superproject gitlink update.

Agents should not add, remove, or reconfigure submodules. When integrating agent branches, prefer cherry-pick or path-limited review so intended code and gitlink updates are accepted without accidental `.gitmodules` or submodule-structure changes.

## Shared Repos

For local-only shared repos, use an ignored bare repo plus per-agent worktrees:

```text
<ws-root>/.shared-repos/<name>.git
<ws-root>/<agent-name>/repos/<name>
```

For `out-of-repo` shared KB, use:

```text
<ws-root>/.shared-repos/shared-kb.git
<ws-root>/<agent-name>/common-kb
```

Create an operator worktree at `<ws-root>/shared-kb` only when useful. Local-only shared repos are not portable across clones unless exported as a Git bundle or pushed to a remote.

## Launch Profiles

During `execute`, adjust launch profiles only after the workspaces exist.

For each profile:

- set or update launch cwd to the planned agent cwd
- preserve unrelated launch settings
- record the old cwd and new cwd in the execution report
- do not rewrite credentials or provider setup except for optional memo-seed changes

If profile format is unclear, inspect existing profile files and follow local patterns. If still unclear, write the intended profile changes in the report and stop before editing them.

## Memo Seeds

If the user opts in, create a Markdown memo seed per agent that combines the original memo seed text with workspace rules.

Memo seed content should include:

- launch cwd
- branch names for superproject and submodules
- writable KB paths
- shared KB paths and ownership
- local-state symlink policy
- submodule commit and push rules
- integration rule: avoid submodule structure changes; expect cherry-pick/path-limited merge

Preserve original memo seed text verbatim in a clearly labeled section, then append workspace rules. Update the launch profile to use the generated memo seed file only after writing it.

Use `houmao-memory-mgr` for direct live-agent memo edits; this skill only prepares launch-profile memo seeds before launch.

## `workspace.md`

Maintain `<ws-root>/workspace.md` as the human-readable map and operating contract. It should record:

- workspace flavor and root
- agents, source profiles, cwd values, and branches
- repo bindings and materialization modes
- local-state symlink decisions
- submodule materialization decisions and status
- shared local repos
- ignored paths
- memo-seed files created
- integration and ownership rules

Treat `workspace.md` as documentation, not as the only source of truth. Inspect Git and the filesystem for status.

## Guardrails

- Do not store Houmao runtime homes, logs, gateways, mailboxes, or generated provider homes inside the workspace layout unless an existing Houmao command chooses that path.
- Do not commit nested Git worktrees into a parent repo.
- Do not overwrite existing worktrees, symlinks, copied repos, local bare repos, or memo seed files without explicit confirmation.
- Do not create two worktrees that check out the same branch from the same Git repo.
- Do not point multiple agents at the same mutable submodule working tree when they are expected to commit independently.
- Do not copy submodule `.git` metadata from one checkout into another worktree.
- Do not let one agent's default writable KB path point into another agent's `kb`.
- Do not treat local-only shared repos as portable unless the user exports or pushes them.
