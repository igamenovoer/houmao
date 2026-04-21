# houmao-utils-workspace-mgr-skill Specification

## Purpose
TBD - created by archiving change consolidate-system-skill-install-sets. Update Purpose after archive.
## Requirements
### Requirement: Packaged workspace-manager utility skill plans and executes workspace preparation
The packaged current-system-skill catalog SHALL include `houmao-utils-workspace-mgr` as a current installable Houmao-owned utility skill.

That packaged skill SHALL use `houmao-utils-workspace-mgr` as both its catalog key and its packaged `asset_subpath`.

The skill SHALL support two explicit operation modes:

- `plan`, which inspects local context and reports the planned workspace organization without mutating files unless the user explicitly asks to write the plan to a Markdown path.
- `execute`, which creates or updates the planned workspace artifacts, Git worktrees, local-only shared repos, ignore rules, optional memo seed files, and launch-profile cwd settings.

If the operation is unclear, the skill SHALL default to `plan`.

The skill SHALL NOT launch agents.

#### Scenario: Plan mode reports a workspace plan without mutation
- **WHEN** the user asks the workspace-manager skill to prepare or inspect a multi-agent workspace without explicitly requesting execution
- **THEN** the skill operates in `plan` mode
- **AND THEN** it reports planned directories, Git actions, local-state symlink decisions, submodule decisions, launch-profile changes, workspace rules, risks, and unresolved questions
- **AND THEN** it does not modify files unless the user supplied a plan output path

#### Scenario: Execute mode prepares the planned workspace
- **WHEN** the user explicitly asks the workspace-manager skill to execute a workspace setup
- **THEN** the skill creates or updates workspace scaffolding, worktrees, local-only shared repos, local-state symlinks, tracked-submodule materialization, `workspace.md`, launch-profile cwd values, and optional memo seed files according to the current plan
- **AND THEN** it reports the resulting workspace state and remaining manual work
- **AND THEN** it does not launch managed agents

### Requirement: Workspace-manager skill separates in-repo and out-of-repo workspace flavors
The packaged `houmao-utils-workspace-mgr` asset SHALL include one top-level `SKILL.md` and separate subskill pages for workspace flavor details.

The top-level skill SHALL load exactly one flavor page after choosing a workspace flavor:

- `subskills/in-repo-workspace.md` for workspaces rooted under the current repository.
- `subskills/out-of-repo-workspace.md` for standalone workspace repositories that mount one or more target repositories.

The in-repo flavor SHALL default the workspace root to `<repo-root>/houmao-ws`.

The in-repo flavor SHALL default each adjusted launch-profile cwd to `<repo-root>` so agents share the parent repository as their visibility surface.

The in-repo flavor SHALL create per-agent repository paths as ignored Git worktrees under each agent workspace and SHALL identify those worktrees as the default mutation surface for source changes and shared-KB changes intended to merge through Git.

The in-repo flavor SHALL identify each agent's parent-checkout KB path as writable only by that owning agent by default.

The out-of-repo flavor SHALL treat `ws-root` as a standalone workspace Git repository that tracks workspace metadata and workspace-owned knowledge rather than target repository code.

#### Scenario: In-repo planning uses the in-repo subskill
- **WHEN** the user requests a workspace rooted inside the current repository
- **THEN** the workspace-manager skill loads `subskills/in-repo-workspace.md`
- **AND THEN** the plan uses `<repo-root>/houmao-ws` by default
- **AND THEN** the plan uses `<repo-root>` as the default launch cwd for each in-repo agent
- **AND THEN** per-agent repository paths are planned as ignored Git worktrees under each agent workspace
- **AND THEN** the plan identifies each agent's private worktree as the write target for source and shared-KB changes intended to merge through Git
- **AND THEN** the plan identifies each agent's parent-checkout KB path as writable only by that owning agent by default

#### Scenario: Out-of-repo planning uses the out-of-repo subskill
- **WHEN** the user requests a standalone multi-repo workspace
- **THEN** the workspace-manager skill loads `subskills/out-of-repo-workspace.md`
- **AND THEN** the plan treats `ws-root` as its own Git repository
- **AND THEN** target repositories are materialized under each agent's `repos/` directory by the selected binding mode

### Requirement: Workspace-manager skill avoids unsafe AI-tool local-state symlinks
The workspace-manager skill SHALL evaluate local-state symlink candidates explicitly instead of blindly applying generic worktree symlink defaults.

For Houmao agent workspaces, the skill SHALL NOT symlink AI tool state directories by default, including `.claude`, `.codex`, `.gemini`, `.aider`, `.cursor`, `.continue`, `.windsurf`, and `.kiro`.

For in-repo Houmao agent workspaces, the skill SHALL default to discovering local-state symlink candidates recursively from the parent checkout without following symlinked directories.

The skill SHALL treat a reachable directory whose basename is `.pixi` as a default local-state symlink candidate when the source subtree contains no Git-tracked files and the destination would not replace tracked content in the worktree.

The skill SHALL treat local-only paths whose basename does not start with `.` as default local-state symlink candidates when the source subtree contains no Git-tracked files and the destination would not replace tracked content in the worktree.

The skill SHALL skip dot-prefixed local-only paths by default, except for reachable `.pixi` directories.

The skill SHALL NOT descend into skipped hidden local-only directories while discovering candidates. Therefore, a nested `.pixi` directory under a skipped hidden local-only parent SHALL NOT be linked by default.

The skill SHALL skip any candidate whose source is missing, whose source subtree contains Git-tracked files, whose source is discovered only by following a symlinked directory, or whose destination would replace tracked content in the worktree.

Every linked or skipped local-state path SHALL be recorded in the plan and in `workspace.md` when execution occurs.

#### Scenario: AI tool homes are skipped by default
- **WHEN** a source repository contains `.claude`, `.codex`, or `.gemini`
- **AND WHEN** the user has not explicitly overridden the local-state symlink policy
- **THEN** the workspace-manager skill does not symlink those directories into agent worktrees
- **AND THEN** it records the skip decision and reason in the workspace plan

#### Scenario: In-repo workspace links reachable pixi and non-hidden local-only paths
- **WHEN** a parent checkout contains reachable local-only paths `.pixi/`, `data-local/`, `src/generated/`, and `packages/api/model-cache/`
- **AND WHEN** those source subtrees contain no Git-tracked files
- **AND WHEN** the user has not explicitly overridden the local-state symlink policy
- **THEN** the workspace-manager skill plans local-state symlinks for `.pixi/`, `data-local/`, `src/generated/`, and `packages/api/model-cache/` into each agent worktree at the same relative paths
- **AND THEN** it records each link decision in the workspace plan and `workspace.md`

#### Scenario: Hidden local-only paths are skipped except reachable pixi
- **WHEN** a parent checkout contains local-only paths `.env`, `.cache/`, `src/.cache/`, `.github/`, and `tools/.pixi/`
- **AND WHEN** `tools/` is traversable without following a symlinked directory
- **AND WHEN** the user has not explicitly overridden the local-state symlink policy
- **THEN** the workspace-manager skill skips `.env`, `.cache/`, `src/.cache/`, and `.github/`
- **AND THEN** it plans a local-state symlink for `tools/.pixi/` when that source subtree contains no Git-tracked files and the destination would not replace tracked content
- **AND THEN** it records the skip and link reasons in the workspace plan

#### Scenario: Hidden parent skip takes precedence over nested pixi
- **WHEN** a parent checkout contains local-only path `.hidden-parent/.pixi/`
- **AND WHEN** the user has not explicitly overridden the local-state symlink policy
- **THEN** the workspace-manager skill skips `.hidden-parent/` as hidden local state
- **AND THEN** it does not descend into `.hidden-parent/`
- **AND THEN** it does not plan a symlink for `.hidden-parent/.pixi/`

#### Scenario: Recursive tracked content blocks a directory candidate
- **WHEN** a parent checkout contains directory `fixtures/`
- **AND WHEN** Git tracks `fixtures/input.json`
- **AND WHEN** `fixtures/` also contains local-only path `fixtures/local-cache.bin`
- **THEN** the workspace-manager skill does not plan a symlink for `fixtures/` as a whole
- **AND THEN** it records that `fixtures/` is skipped because the source subtree contains tracked content
- **AND THEN** it may still consider narrower local-only non-hidden descendants according to the same candidate rules

#### Scenario: Symlinked directories are not followed during discovery
- **WHEN** a parent checkout contains a symlinked directory `external-state/`
- **AND WHEN** the symlink target contains local-only non-hidden paths or `.pixi/`
- **AND WHEN** the user has not explicitly overridden the local-state symlink policy
- **THEN** the workspace-manager skill does not follow `external-state/` during candidate discovery
- **AND THEN** it records the skip reason in the workspace plan

### Requirement: Workspace-manager skill materializes tracked submodules without redundant checkout by default
Tracked submodule content SHALL be accessible inside agent worktrees, and agents SHALL be able to create branches, commit normally, and push inside submodules when a remote is configured.

The workspace-manager skill SHALL support these tracked-submodule materialization modes:

- `seeded-worktree`, the default mode, which creates a real Git worktree for each initialized source submodule inside the agent worktree and seeds files from the source checkout without copying `.git` metadata.
- `empty`, which leaves the submodule uninitialized or empty.
- `checkout`, which runs a normal `git submodule update --init --recursive` inside the agent worktree.

In `seeded-worktree` mode, the skill SHALL require the source checkout submodule to be initialized, create an agent-owned submodule branch, preserve the new worktree `.git` file, avoid copying source `.git` metadata, and report dirty state when seeded files do not match the superproject-recorded submodule commit.

The skill SHALL instruct agents that submodule commits require a corresponding superproject gitlink commit and that submodule branches should be pushed before relying on superproject gitlink updates.

#### Scenario: Default submodule handling creates branchable submodule worktrees
- **WHEN** a tracked submodule is initialized in the source checkout
- **AND WHEN** the user does not choose another submodule mode
- **THEN** the workspace-manager skill plans `seeded-worktree` materialization for that submodule
- **AND THEN** execution creates a real submodule Git worktree on an agent-owned branch inside the agent worktree
- **AND THEN** the agent can commit inside the submodule and commit the updated gitlink in the superproject branch

#### Scenario: Uninitialized source submodule blocks seeded worktree execution
- **WHEN** the selected submodule mode is `seeded-worktree`
- **AND WHEN** the source checkout submodule is not initialized
- **THEN** execution fails or stops for that submodule before creating an invalid seeded worktree
- **AND THEN** the report tells the operator to initialize the source submodule or select a different materialization mode

### Requirement: Workspace-manager skill maintains workspace operating documentation
The workspace-manager skill SHALL maintain `<ws-root>/workspace.md` as a human-readable map and operating contract when execution occurs.

`workspace.md` SHALL record the workspace flavor and root, agents and launch-profile bindings, branch names, repo bindings and materialization modes, local-state symlink decisions, submodule materialization decisions, shared local repos, ignored paths, memo seed files created, and integration or ownership rules.

For in-repo workspaces, `workspace.md` SHALL record that `<repo-root>` is the shared launch cwd and visibility surface.

For in-repo workspaces, `workspace.md` SHALL record read/write ownership rules for:

- parent-checkout source paths
- each agent's private worktree
- each agent's private worktree copy of `houmao-ws/shared-kb`
- parent-checkout `houmao-ws/shared-kb`
- each agent's parent-checkout `houmao-ws/<agent-name>/kb`
- sibling agents' KB directories and worktrees
- `workspace.md` itself

The skill SHALL treat `workspace.md` as documentation rather than the only source of truth.

#### Scenario: Execution writes a workspace map
- **WHEN** the workspace-manager skill executes a workspace setup
- **THEN** it writes or updates `<ws-root>/workspace.md`
- **AND THEN** the file documents the workspace layout, Git branch rules, submodule policy, and shared knowledge paths needed by operators and agents

#### Scenario: In-repo workspace map records shared visibility and private mutation rules
- **WHEN** the workspace-manager skill executes an in-repo workspace setup
- **THEN** `<ws-root>/workspace.md` records `<repo-root>` as the default launch cwd
- **AND THEN** it marks parent-checkout source paths as read-only by default for agents
- **AND THEN** it marks each agent's private worktree as writable by that agent for source changes
- **AND THEN** it marks each agent's private worktree copy of `houmao-ws/shared-kb` as writable by that agent for shared-KB changes intended to merge through Git
- **AND THEN** it marks each agent's parent-checkout `houmao-ws/<agent-name>/kb` as writable only by that owning agent by default
- **AND THEN** it marks sibling KB directories, sibling worktrees, and `workspace.md` as read-only by default for non-owning agents

### Requirement: Workspace-manager skill can prepare launch-profile memo seeds with workspace rules
When the user opts in, the workspace-manager skill SHALL create per-agent Markdown memo seed files that preserve original memo seed text and append workspace-specific rules.

The appended workspace rules SHALL include launch cwd, branch names, writable knowledge paths, shared knowledge paths, local-state symlink policy, submodule commit and push rules, and the integration rule that agents should avoid submodule add/delete/reconfigure changes.

For in-repo workspaces, the appended workspace rules SHALL state that the launch cwd is `<repo-root>`, source modifications belong in the agent's private worktree, shared-KB modifications intended for Git merge belong in the agent's private worktree copy of `houmao-ws/shared-kb`, the agent may write its own parent-checkout KB path, and sibling KB directories and worktrees are read-only by default.

The workspace-manager skill SHALL update launch profiles to use generated memo seed files only after writing those files.

The skill SHALL route direct live-agent memo edits to `houmao-memory-mgr` rather than editing live `houmao-memo.md` files itself.

#### Scenario: Optional memo seed preserves original text and appends workspace rules
- **WHEN** the user asks execution to seed workspace rules into agent memo seeds
- **THEN** the skill creates per-agent Markdown memo seed files
- **AND THEN** each generated file preserves the original memo seed text in a labeled section and appends the planned workspace rules
- **AND THEN** launch profiles are updated to reference the generated memo seed files

#### Scenario: In-repo memo seed describes safe write targets
- **WHEN** the user asks execution to seed workspace rules into agent memo seeds for an in-repo workspace
- **THEN** each generated memo seed records `<repo-root>` as the launch cwd and shared visibility surface
- **AND THEN** it instructs the agent to make source changes in its private worktree
- **AND THEN** it instructs the agent to make shared-KB changes intended for Git merge in its private worktree copy of `houmao-ws/shared-kb`
- **AND THEN** it identifies the agent's own parent-checkout KB path as writable for agent-owned notes
- **AND THEN** it identifies sibling KB directories and sibling worktrees as read-only by default

### Requirement: Workspace-manager remains the standard workspace-preparation skill
The packaged `houmao-utils-workspace-mgr` guidance SHALL remain the Houmao-owned standard workspace-preparation surface.

The skill SHALL support preparing Houmao-standard workspace layouts and SHALL NOT add a `custom` workspace lane that attempts to absorb arbitrary operator-owned workspace contracts.

Users who do not want the Houmao-standard workspace posture SHALL be able to avoid invoking `houmao-utils-workspace-mgr` instead of routing their custom layout through it.

#### Scenario: Custom workspace is not a workspace-manager lane
- **WHEN** an operator wants a nonstandard workspace layout for a loop run
- **THEN** the loop plan may record that custom layout directly
- **AND THEN** `houmao-utils-workspace-mgr` does not need to expose that custom layout as one of its own operating modes

### Requirement: In-repo workspace-manager posture is task-scoped
The loop-facing in-repo posture of `houmao-utils-workspace-mgr` SHALL be task-scoped under:

```text
<repo-root>/houmao-ws/<task-name>
```

For task-scoped in-repo workspaces, the task root SHALL contain:

- `workspace.md` as the task-local operating contract,
- `shared-kb/` as the task-local shared knowledge surface,
- one directory per agent beneath the task root.

The repo-level `houmao-ws/workspaces.md` MAY act as an index across task workspaces, but it SHALL NOT replace each task-local `workspace.md` as the authoritative contract for that team.

Task-scoped in-repo workspaces SHALL use task-qualified branch names such as:

```text
houmao/<task-name>/<agent-name>/main
```

#### Scenario: Two in-repo teams can coexist with the same agent names
- **WHEN** one repository hosts two task-scoped in-repo workspaces with different `task-name` values
- **THEN** each task receives its own task root, task-local `workspace.md`, task-local `shared-kb`, and task-qualified branches
- **AND THEN** the two teams can reuse the same `agent-name` values without path or branch collisions

### Requirement: Workspace-manager skill can publish loop-facing standard workspace posture summaries
The packaged `houmao-utils-workspace-mgr` guidance SHALL support loop-facing summaries for prepared standard workspace postures so loop plans can reference prepared workspace behavior without restating the full workspace layout from scratch.

For each prepared agent workspace, a loop-facing summary SHALL identify:

- the selected workspace flavor,
- the selected `task-name` and task root for in-repo mode,
- the shared visibility surface or launch cwd,
- the private source-mutation surface,
- shared writable surfaces when applicable,
- default read-only shared surfaces,
- ad hoc worktree posture,
- task-qualified branch names when applicable,
- the relevant `workspace.md` reference when one exists.

The loop-facing summary SHALL describe writable bookkeeping zones only at the level of allowed standard surfaces. It SHALL NOT prescribe a fixed subtree under per-agent `kb/`.

#### Scenario: In-repo workspace summary is reusable by a loop plan
- **WHEN** the workspace-manager skill prepares or plans an in-repo workspace for loop participants
- **THEN** the resulting plan or task-local `workspace.md` can summarize the task root, shared visibility surface, and private mutation surface for each agent
- **AND THEN** it does not require a loop plan to invent a separate standard in-repo workspace contract from scratch
