## ADDED Requirements

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
