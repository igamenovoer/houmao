## ADDED Requirements

### Requirement: In-repo workspace collection is untracked local state
The in-repo workspace-manager posture SHALL treat `<repo-root>/houmao-ws` as an untracked local workspace collection directory.

The workspace-manager skill SHALL keep the in-repo workspace collection out of the parent repository's tracked file set by default.

Execution SHALL prefer a local ignore rule in `.git/info/exclude` for `houmao-ws/` unless the user explicitly requests a tracked ignore-file update.

The in-repo workspace collection SHALL contain local coordination material, task knowledge, owner state, workspace maps, and per-agent worktree containers, but SHALL NOT itself be a Git-tracked collaboration surface.

#### Scenario: Execution excludes the workspace collection locally
- **WHEN** the workspace-manager skill executes an in-repo workspace setup using the default workspace collection
- **THEN** it ensures `houmao-ws/` is ignored from the parent repository's tracked file set
- **AND THEN** it prefers recording that ignore rule in `.git/info/exclude`
- **AND THEN** it reports the ignore decision in the plan or resulting workspace summary

#### Scenario: In-repo workspace state is not a Git merge surface
- **WHEN** an in-repo workspace contains `workspace.md`, `shared-kb/`, `states/`, or agent bookkeeping files under `<repo-root>/houmao-ws/<task-name>`
- **THEN** the workspace-manager guidance identifies those paths as untracked local workspace state
- **AND THEN** it does not instruct agents to commit or merge those paths through the parent repository

## MODIFIED Requirements

### Requirement: Workspace-manager skill separates in-repo and out-of-repo workspace flavors
The packaged `houmao-utils-workspace-mgr` asset SHALL include one top-level `SKILL.md` and separate subskill pages for workspace flavor details.

The top-level skill SHALL load exactly one flavor page after choosing a workspace flavor:

- `subskills/in-repo-workspace.md` for untracked local workspaces rooted under the current repository.
- `subskills/out-of-repo-workspace.md` for standalone workspace repositories that mount one or more target repositories.

The in-repo flavor SHALL default the workspace collection root to `<repo-root>/houmao-ws`.

The in-repo flavor SHALL default each adjusted launch-profile cwd to `<repo-root>` so agents share the parent repository as their visibility surface.

The in-repo flavor SHALL create per-agent repository paths as ignored Git worktrees under each task-local agent workspace and SHALL identify those worktrees as the default mutation surface for source changes intended to merge through Git.

The in-repo flavor SHALL identify task-local `shared-kb/` as untracked cross-run task knowledge and task-local `owner-states/<subdir>/...` as untracked per-run task-owner bookkeeping.

The out-of-repo flavor SHALL treat `ws-root` as a standalone workspace Git repository that tracks workspace metadata and workspace-owned knowledge rather than target repository code.

#### Scenario: In-repo planning uses the in-repo subskill
- **WHEN** the user requests a workspace rooted inside the current repository
- **THEN** the workspace-manager skill loads `subskills/in-repo-workspace.md`
- **AND THEN** the plan uses `<repo-root>/houmao-ws` as the default untracked workspace collection
- **AND THEN** the plan uses `<repo-root>` as the default launch cwd for each in-repo agent
- **AND THEN** per-agent repository paths are planned as ignored Git worktrees under each task-local agent workspace
- **AND THEN** the plan identifies each agent's private worktree as the write target for source changes intended to merge through Git
- **AND THEN** the plan identifies task-local `shared-kb/` as cross-run shared knowledge and task-local `owner-states/<subdir>/...` as per-run task-owner bookkeeping

#### Scenario: Out-of-repo planning uses the out-of-repo subskill
- **WHEN** the user requests a standalone multi-repo workspace
- **THEN** the workspace-manager skill loads `subskills/out-of-repo-workspace.md`
- **AND THEN** the plan treats `ws-root` as its own Git repository
- **AND THEN** target repositories are materialized under each agent's `repos/` directory by the selected binding mode

### Requirement: Workspace-manager skill maintains workspace operating documentation
The workspace-manager skill SHALL maintain `<task-root>/workspace.md` as a human-readable map and operating contract when execution occurs for an in-repo task workspace.

For non-task-scoped workspace modes, the workspace-manager skill SHALL maintain the applicable workspace map at the selected workspace root.

`workspace.md` SHALL record the workspace flavor and root, agents and launch-profile bindings, branch names, repo bindings and materialization modes, local-state symlink decisions, submodule materialization decisions, shared local repos, ignored paths, memo seed files created, and integration or ownership rules.

For in-repo workspaces, `workspace.md` SHALL record that `<repo-root>` is the shared launch cwd and visibility surface.

For in-repo workspaces, `workspace.md` SHALL record that `<repo-root>/houmao-ws` is an untracked local workspace collection.

For in-repo workspaces, `workspace.md` SHALL record read/write ownership rules for:

- parent-checkout source paths
- each agent's private worktree
- task-local `shared-kb/`
- task-local `owner-states/<subdir>/...`
- each agent's local bookkeeping surface
- sibling agents' bookkeeping directories and worktrees
- `workspace.md` itself

The skill SHALL treat `workspace.md` as documentation rather than the only source of truth.

#### Scenario: Execution writes a workspace map
- **WHEN** the workspace-manager skill executes a workspace setup
- **THEN** it writes or updates the applicable `workspace.md`
- **AND THEN** the file documents the workspace layout, Git branch rules, submodule policy, shared knowledge paths, owner-state paths, and ownership rules needed by operators and agents

#### Scenario: In-repo workspace map records shared visibility and private mutation rules
- **WHEN** the workspace-manager skill executes an in-repo workspace setup
- **THEN** `<task-root>/workspace.md` records `<repo-root>` as the default launch cwd
- **AND THEN** it marks parent-checkout source paths as read-only by default for agents
- **AND THEN** it marks each agent's private worktree as writable by that agent for source changes
- **AND THEN** it marks task-local `shared-kb/` as untracked cross-run task knowledge
- **AND THEN** it marks task-local `owner-states/<subdir>/...` as untracked per-run task-owner bookkeeping
- **AND THEN** it marks sibling agent bookkeeping directories, sibling worktrees, and `workspace.md` as read-only by default for non-owning agents

### Requirement: Workspace-manager skill can prepare launch-profile memo seeds with workspace rules
When the user opts in, the workspace-manager skill SHALL create per-agent Markdown memo seed files that preserve original memo seed text and append workspace-specific rules.

The appended workspace rules SHALL include launch cwd, branch names, writable knowledge paths, shared knowledge paths, owner-state paths, local-state symlink policy, submodule commit and push rules, and the integration rule that agents should avoid submodule add/delete/reconfigure changes.

For in-repo workspaces, the appended workspace rules SHALL state that the launch cwd is `<repo-root>`, source modifications belong in the agent's private worktree, task shared knowledge belongs in the untracked task-local `shared-kb/`, per-run task-owner bookkeeping belongs in untracked task-local `owner-states/<subdir>/...`, and sibling bookkeeping directories and worktrees are read-only by default.

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
- **AND THEN** it identifies task-local `shared-kb/` as untracked cross-run shared task knowledge
- **AND THEN** it identifies task-local `owner-states/<subdir>/...` as untracked per-run task-owner bookkeeping
- **AND THEN** it identifies sibling bookkeeping directories and sibling worktrees as read-only by default

### Requirement: In-repo workspace-manager posture is task-scoped
The loop-facing in-repo posture of `houmao-utils-workspace-mgr` SHALL be task-scoped under:

```text
<repo-root>/houmao-ws/<task-name>
```

For task-scoped in-repo workspaces, the task root SHALL contain:

- `workspace.md` as the task-local operating contract,
- `shared-kb/` as the untracked task-local shared knowledge surface that may persist across runs,
- `owner-states/` as the untracked task-local container for per-run task-owner bookkeeping subdirectories,
- one directory per agent beneath the task root.

The repo-level `houmao-ws/workspaces.md` MAY act as a local untracked index across task workspaces, but it SHALL NOT replace each task-local `workspace.md` as the authoritative contract for that team.

Task-scoped in-repo workspaces SHALL use task-qualified branch names such as:

```text
houmao/<task-name>/<agent-name>/main
```

#### Scenario: Two in-repo teams can coexist with the same agent names
- **WHEN** one repository hosts two task-scoped in-repo workspaces with different `task-name` values
- **THEN** each task receives its own task root, task-local `workspace.md`, task-local `shared-kb`, task-local `owner-states`, and task-qualified branches
- **AND THEN** the two teams can reuse the same `agent-name` values without path or branch collisions

#### Scenario: Shared knowledge persists across runs while states are run-scoped
- **WHEN** a task workspace is reused for multiple runs
- **THEN** task knowledge that should survive across runs is recorded under `<task-root>/shared-kb/`
- **AND THEN** per-run task-owner bookkeeping is recorded under `<task-root>/owner-states/<subdir>/...`

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

For in-repo mode, the loop-facing summary SHALL identify `<repo-root>/houmao-ws` as the untracked workspace collection, `<task-root>/shared-kb/` as cross-run shared task knowledge, and `<task-root>/owner-states/<subdir>/...` as per-run task-owner bookkeeping when an owner-state subdir is selected.

The loop-facing summary SHALL describe writable bookkeeping zones only at the level of allowed standard surfaces. It SHALL NOT prescribe a fixed subtree under per-agent bookkeeping directories.

#### Scenario: In-repo workspace summary is reusable by a loop plan
- **WHEN** the workspace-manager skill prepares or plans an in-repo workspace for loop participants
- **THEN** the resulting plan or task-local `workspace.md` can summarize the task root, shared visibility surface, private mutation surface, shared knowledge surface, and owner-state surface for each agent
- **AND THEN** it does not require a loop plan to invent a separate standard in-repo workspace contract from scratch
