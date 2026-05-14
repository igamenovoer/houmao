# houmao-agent-loop-pairwise-skill Specification

## Purpose
TBD - created by archiving change add-houmao-agent-loop-pairwise-skill. Update Purpose after archive.
## Requirements
### Requirement: The authoring lane formulates user intent into an explicit pairwise loop plan
The authoring guidance in `houmao-agent-loop-pairwise` SHALL turn natural-language user intent into one explicit pairwise loop plan before run start.

That authored plan SHALL support two forms:

- one single-file Markdown plan,
- one bundle directory with `plan.md` as the canonical entrypoint plus referenced supporting Markdown files or scripts.

Every authored plan SHALL identify at minimum:

- the designated master,
- the allowed participant set,
- the objective,
- the completion condition,
- the stop policy,
- the reporting contract,
- any referenced scripts and their caller or side-effect contract.

The authoring guidance SHALL normalize delegation authority explicitly rather than treating delegation as free by default.

At minimum, the guidance SHALL support these delegation postures:

- no delegation,
- delegation only to a named set,
- free delegation within a named set,
- free delegation to any agent.

When the plan does not explicitly authorize free delegation, the authored result SHALL preserve that restriction rather than silently widening it.

#### Scenario: Single-file plan captures a small pairwise loop
- **WHEN** a user asks for a smaller pairwise loop that does not need many supporting files
- **THEN** the authoring guidance may produce one Markdown plan file
- **AND THEN** that file still records the master, participants, delegation policy, completion condition, and stop policy explicitly

#### Scenario: Bundle plan captures a structured pairwise run contract
- **WHEN** a user asks for a larger pairwise loop that needs supporting notes or scripts
- **THEN** the authoring guidance may produce one bundle directory with `plan.md` as the canonical entrypoint
- **AND THEN** the supporting files remain focused on the run contract rather than on standalone prestart preparation briefs

#### Scenario: Delegation remains restricted when the user does not grant free delegation
- **WHEN** a user's request names allowed downstream agents but does not authorize free delegation beyond them
- **THEN** the authored plan records that restricted delegation policy explicitly
- **AND THEN** the master is not instructed to improvise broader delegation authority

### Requirement: The authored plan includes a Mermaid control graph that distinguishes execution from supervision
Every finalized pairwise loop plan produced by `houmao-agent-loop-pairwise` SHALL include a Mermaid fenced diagram that visualizes the final loop graph.

That diagram SHALL show at minimum:

- the user agent outside the execution loop,
- the designated master as the root run owner,
- the pairwise immediate-control edges between drivers and workers,
- where the supervision loop lives,
- where the completion condition is evaluated,
- where the stop condition is evaluated.

The graph guidance SHALL treat the execution topology as pairwise local-close routing and SHALL distinguish that topology from the supervisor review loop that keeps the run alive.

The graph guidance SHALL NOT require or imply an arbitrary cyclic worker-to-worker execution graph as the default model.

#### Scenario: Final plan includes a top-level Mermaid graph
- **WHEN** the authoring guidance finishes one pairwise loop plan
- **THEN** the final plan includes a Mermaid fenced code block for the top-level control graph
- **AND THEN** it does not fall back to plain-text ASCII art as the primary graph representation

#### Scenario: Diagram makes the supervision loop explicit
- **WHEN** a reader inspects the final graph in the authored plan
- **THEN** the graph shows where the master's review or supervision loop runs
- **AND THEN** it distinguishes that loop from the immediate pairwise execution edges between agents

### Requirement: The operating lane treats the user agent as outside the loop and places liveness on the master
The lifecycle guidance in `houmao-agent-loop-pairwise` SHALL define the stable operator actions for pairwise loop control while keeping the user agent outside the execution loop and placing accepted-run liveness on the designated master.

The operating guidance SHALL include at minimum:

- `start`,
- `status`,
- `stop`.

The lifecycle guidance SHALL define `start` as the action that sends the normalized start trigger only to the designated master.

The lifecycle guidance SHALL define `status` as a periodic read-only status request to the designated master for one `run_id`.

After accepting a run, the designated master SHALL be described as the owner of:

- root run state under one user-visible `run_id`,
- liveness and supervision,
- downstream pairwise dispatch,
- final completion evaluation,
- stop handling and stop-result summary.

The lifecycle guidance SHALL define `stop` as a master-directed termination action by default.

The lifecycle guidance SHALL NOT redefine `stop` as an implicit participant-wide broadcast.

The lifecycle guidance SHALL continue to state that downstream execution uses the elemental pairwise edge-loop pattern for each immediate driver-worker edge rather than a new routing protocol.

The lifecycle guidance SHALL keep composed run topology in the accepted pairwise loop plan rather than pushing multi-edge graph planning down into `houmao-adv-usage-pattern`.

#### Scenario: Status remains the stable read-only inspection verb
- **WHEN** the operator asks for `status` on one accepted pairwise loop run
- **THEN** the lifecycle guidance treats that request as read-only master-owned inspection
- **AND THEN** it does not redefine `status` as `peek`, `ping`, or any other enriched v2 control verb

#### Scenario: Stop remains master-directed
- **WHEN** the operator asks to `stop` one active pairwise loop run
- **THEN** the lifecycle guidance routes that stop request to the designated master
- **AND THEN** it does not implicitly redefine `stop` as a participant-wide broadcast mail action

#### Scenario: Stable pairwise run control excludes the enriched v2 operator verbs
- **WHEN** a reader opens the packaged `houmao-agent-loop-pairwise` operating guidance
- **THEN** the stable run-control surface is described through `start`, `status`, and `stop`
- **AND THEN** enriched v2-only verbs such as `initialize`, `peek`, `ping`, `pause`, `resume`, or `hard-kill` are not described as part of the stable skill contract

### Requirement: Stable pairwise-named loop skill presents tree loop terminology
The packaged `houmao-agent-loop-pairwise` skill SHALL keep its skill name, packaged asset directory name, and explicit activation handle unchanged.

The skill SHALL describe its authored topology as a tree loop or local-close tree loop in user-facing explanatory text.

The skill SHALL present `pairwise loop` as a legacy alias for tree loop behavior rather than as the primary concept name.

The skill SHALL keep pairwise-named protocol references only where they identify existing skill handles, compatibility aliases, or elemental local-close edge behavior.

#### Scenario: Stable skill is invoked by legacy name
- **WHEN** a user explicitly invokes `houmao-agent-loop-pairwise`
- **THEN** the skill remains the correct packaged entrypoint
- **AND THEN** its guidance explains that the run is a tree loop with pairwise loop as an alias

#### Scenario: Stable skill routes to elemental edge protocol
- **WHEN** stable tree-loop guidance points to one immediate driver-worker edge protocol
- **THEN** it uses local-close edge loop terminology
- **AND THEN** it may mention the existing pairwise edge-loop pattern as the compatibility target

### Requirement: Stable pairwise skill is retired
The system SHALL NOT package `houmao-agent-loop-pairwise` as a current installable Houmao-owned system skill.

Current guidance SHALL route tree-loop authoring and execution through `houmao-agent-loop-pro`.

#### Scenario: Stable pairwise name is absent from current inventory
- **WHEN** the current system-skill inventory is loaded
- **THEN** `houmao-agent-loop-pairwise` is not present as a current installable skill
- **AND THEN** `houmao-agent-loop-pro` is present as the current loop skill
