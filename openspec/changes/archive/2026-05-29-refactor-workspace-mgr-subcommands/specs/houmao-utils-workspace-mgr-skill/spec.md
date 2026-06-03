## ADDED Requirements

### Requirement: Workspace-manager entrypoint is a concise operation router
The packaged `houmao-utils-workspace-mgr` top-level `SKILL.md` SHALL act as a concise router rather than a long-form policy document.

The top-level entrypoint SHALL include structured sections for activation, help, operations, routing, shared references, and constraints.

The top-level entrypoint SHALL list supported operations in a Markdown table or compact Markdown list that explains what each operation does and when to use it.

Detailed operation behavior SHALL live in routed operation pages, flavor pages, or reference pages rather than the top-level entrypoint.

#### Scenario: Help exposes concise operations
- **WHEN** the user asks for workspace-manager help or usage
- **THEN** the response is based on the top-level operation list
- **AND THEN** the response describes `plan`, `create`, `validate`, and `summarize` without loading detailed policy pages unnecessarily

#### Scenario: Concrete operation routes to one operation page
- **WHEN** the user invokes a concrete workspace-manager operation
- **THEN** the skill routes to the matching operation page
- **AND THEN** it loads only the selected flavor and reference pages needed for that operation

### Requirement: Workspace-manager validates project-scope worktree readiness
The workspace-manager skill SHALL support a `validate` operation that checks prepared workspace readiness without creating or repairing workspace topology.

Validation SHALL verify that planned or created worktrees exist, use the expected branch posture, and have required local-state links or materialized paths needed for project-scope commands.

Validation SHALL support project-scope tool checks for project-managed commands such as Pixi commands, virtual-environment Python commands, C or C++ build commands, and in-project scripts when those commands are discovered safely or supplied explicitly by the operator.

Validation SHALL prefer explicit operator-provided validation commands and documented project commands over inventing expensive build or test commands.

Validation SHALL report commands considered, commands run, skipped commands, missing local state, failed checks, and recommended follow-up actions.

Validation SHALL NOT mutate workspace topology, create worktrees, rewrite launch profiles, or change workspace ownership rules. Validation MAY allow invoked project tools to create their normal cache, build, or environment outputs.

#### Scenario: Validate reports missing local-state links
- **WHEN** a prepared worktree is missing a required local-state link or materialized path from the workspace plan
- **THEN** `validate` reports the missing path and expected source
- **AND THEN** it recommends rerunning `create` with the appropriate local-state decision or manually repairing the path

#### Scenario: Validate runs project-scope commands
- **WHEN** the operator supplies validation commands or the project exposes safe documented commands
- **THEN** `validate` runs those commands from the prepared worktree or selected project cwd
- **AND THEN** it reports success or failure for each command

#### Scenario: Validate avoids invented heavy commands
- **WHEN** a project contains build configuration but no explicit safe validation command is supplied or documented
- **THEN** `validate` reports candidate tooling without inventing a heavy build command
- **AND THEN** it asks for or records the needed validation command before running it

## MODIFIED Requirements

### Requirement: Packaged workspace-manager utility skill plans and executes workspace preparation
The packaged current-system-skill catalog SHALL include `houmao-utils-workspace-mgr` as a current installable Houmao-owned utility skill.

That packaged skill SHALL use `houmao-utils-workspace-mgr` as both its catalog key and its packaged `asset_subpath`.

The skill SHALL support these explicit operation modes:

- `help`, which explains this skill's independent workspace-preparation purpose, operation list, common prompts, and related-skill boundaries without planning or mutating files.
- `plan`, which inspects local context and reports the planned workspace organization without mutating files unless the user explicitly asks to write the plan to a Markdown path.
- `create`, which creates or updates the planned workspace artifacts, Git worktrees, local-only shared repos, ignore rules, local-state links, optional memo seed files, and launch-profile cwd settings.
- `validate`, which checks prepared workspace and worktree readiness, including project-scope tool availability and required local-state links, without creating or repairing workspace topology.
- `summarize`, which reports compact prepared-workspace facts for humans, scripts, or upstream planners.

If the operation is unclear, the skill SHALL default to `plan`.

The skill MAY treat `execute` as a compatibility alias for `create`, but `create` SHALL be the standard mutating setup operation name.

The skill SHALL NOT launch agents.

#### Scenario: Plan mode reports a workspace plan without mutation
- **WHEN** the user asks the workspace-manager skill to prepare or inspect a multi-agent workspace without explicitly requesting creation
- **THEN** the skill operates in `plan` mode
- **AND THEN** it reports planned directories, Git actions, local-state link decisions, submodule decisions, launch-profile changes, workspace rules, risks, and unresolved questions
- **AND THEN** it does not modify files unless the user supplied a plan output path

#### Scenario: Create mode prepares the planned workspace
- **WHEN** the user explicitly asks the workspace-manager skill to create a workspace setup
- **THEN** the skill creates or updates workspace scaffolding, worktrees, local-only shared repos, local-state links, tracked-submodule materialization, `workspace.md`, launch-profile cwd values, and optional memo seed files according to the current plan
- **AND THEN** it reports the resulting workspace state and remaining manual work
- **AND THEN** it does not launch managed agents

#### Scenario: Execute aliases create during transition
- **WHEN** the user invokes `execute` for a workspace setup
- **THEN** the skill treats the request as `create` or clearly reports that `create` is the replacement operation
- **AND THEN** it does not expose a separate behavior path for `execute`

#### Scenario: Summarize reports prepared workspace facts
- **WHEN** the user asks for a summary of a planned or prepared workspace
- **THEN** the skill reports workspace flavor, root paths, agent worktree paths, branch names, shared knowledge paths, local-state posture, validation posture, and relevant `workspace.md` references

### Requirement: Workspace-manager remains the standard workspace-preparation skill
The packaged `houmao-utils-workspace-mgr` guidance SHALL remain the Houmao-owned standard workspace-preparation and workspace-validation surface.

The skill SHALL support preparing, validating, and summarizing Houmao-standard workspace layouts and SHALL NOT add a `custom` workspace lane that attempts to absorb arbitrary operator-owned workspace contracts.

The skill SHALL describe upstream requirements and downstream consumers generically. It SHALL NOT make loop plans, loop execplans, or `houmao-agent-loop-pro` part of its own contract.

Users who do not want the Houmao-standard workspace posture SHALL be able to avoid invoking `houmao-utils-workspace-mgr` instead of routing their custom layout through it.

#### Scenario: Custom workspace is not a workspace-manager lane
- **WHEN** an operator wants a nonstandard workspace layout
- **THEN** an upstream plan or operator note may record that custom layout directly
- **AND THEN** `houmao-utils-workspace-mgr` does not need to expose that custom layout as one of its own operating modes

#### Scenario: Workspace-manager remains independent of loop skills
- **WHEN** workspace-manager guidance describes prepared workspace summaries, bookkeeping requests, validation, or downstream consumers
- **THEN** it uses workspace-oriented language
- **AND THEN** it does not describe those concepts as loop-facing or loop-owned

### Requirement: Workspace-manager skill can publish loop-facing standard workspace posture summaries
The packaged `houmao-utils-workspace-mgr` guidance SHALL support consumer-neutral summaries for prepared standard workspace postures so humans, scripts, or upstream planners can reference prepared workspace behavior without restating the full workspace layout from scratch.

For each prepared agent workspace, a workspace summary SHALL identify:

- the selected workspace flavor,
- the selected `task-name` and task root for in-repo mode,
- the shared visibility surface or launch cwd,
- the private source-mutation surface,
- shared writable surfaces when applicable,
- default read-only shared surfaces,
- local-state link posture,
- validation posture when validation has run,
- ad hoc worktree posture,
- task-qualified branch names when applicable,
- the relevant `workspace.md` reference when one exists.

The workspace summary SHALL describe writable bookkeeping zones only at the level of allowed standard surfaces. It SHALL NOT prescribe a fixed subtree under per-agent bookkeeping directories.

#### Scenario: Workspace summary is reusable by downstream consumers
- **WHEN** the workspace-manager skill prepares, plans, validates, or summarizes a workspace for participants
- **THEN** the resulting plan, validation report, summary, or `workspace.md` can summarize the workspace root, shared visibility surface, private mutation surface, local-state posture, and validation posture for each agent
- **AND THEN** it does not require downstream consumers to invent a separate standard workspace contract from scratch
