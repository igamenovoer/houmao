## ADDED Requirements

### Requirement: Workspace-manager skill can publish loop-facing standard workspace posture summaries
The packaged `houmao-utils-workspace-mgr` guidance SHALL support loop-facing summaries for prepared standard workspace postures so loop plans can reference prepared workspace behavior without restating the full workspace layout from scratch.

For each prepared agent workspace, a loop-facing summary SHALL identify:

- the selected workspace flavor,
- the shared visibility surface or launch cwd,
- the private source-mutation surface,
- shared writable surfaces when applicable,
- default read-only shared surfaces,
- ad hoc worktree posture,
- the relevant `workspace.md` reference when one exists.

The loop-facing summary SHALL describe writable bookkeeping zones only at the level of allowed surfaces. It SHALL NOT impose a fixed subtree under per-agent `kb/`.

#### Scenario: In-repo workspace summary is reusable by a loop plan
- **WHEN** the workspace-manager skill prepares or plans an in-repo workspace for loop participants
- **THEN** the resulting plan or `workspace.md` can summarize the shared visibility surface and private mutation surface for each agent
- **AND THEN** it does not require a loop plan to invent a separate in-repo workspace contract from scratch

#### Scenario: Loop-facing summary does not impose a bookkeeping tree
- **WHEN** the workspace-manager skill reports loop-facing standard workspace posture for an agent
- **THEN** it may identify the agent-owned writable zones available for bookkeeping
- **AND THEN** it does not prescribe a fixed file tree under that agent's `kb/` directory
