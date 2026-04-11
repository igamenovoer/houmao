# houmao-agent-loop-pairwise-skill Specification

## Purpose
TBD - created by archiving change add-houmao-agent-loop-pairwise-skill. Update Purpose after archive.
## Requirements
### Requirement: Houmao provides a packaged `houmao-agent-loop-pairwise` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-loop-pairwise` under the maintained system-skill asset root.

That packaged skill SHALL use `houmao-agent-loop-pairwise` as both its skill name and its packaged asset directory name under `src/houmao/agents/assets/system_skills/`.

The top-level `SKILL.md` for that packaged skill SHALL describe the skill as a user-controlled manual pairwise loop-planning and run-control skill rather than as a new runtime workflow engine or the versioned enriched pairwise surface.

The packaged `houmao-agent-loop-pairwise` skill SHALL be manual-invocation-only. It SHALL instruct agents to use the skill only when the user explicitly asks for `houmao-agent-loop-pairwise` by name.

That packaged skill SHALL organize its guidance through local authoring and operating pages beneath the same packaged skill directory.

That packaged skill SHALL remain distinct from the direct-operation skills, the existing `houmao-adv-usage-pattern` pattern pages that it composes, and the versioned `houmao-agent-loop-pairwise-v2` skill.

That packaged skill SHALL own composed pairwise loop planning concerns, including multi-edge topology, recursive child-control edges, rendered control graphs, master-owned run planning, run charters, and `start`/`status`/`stop` run-control actions.

When that packaged skill references `houmao-adv-usage-pattern`, it SHALL treat the advanced-usage pairwise page as the elemental immediate driver-worker edge protocol to use per edge rather than as the owner of composed pairwise topology.

That packaged skill SHALL NOT present itself as the default entrypoint for generic pairwise loop planning or pairwise run-control requests when the user did not explicitly invoke the skill by name.

#### Scenario: User explicitly asks to invoke the restored stable pairwise skill
- **WHEN** a user explicitly asks for `houmao-agent-loop-pairwise`
- **THEN** `houmao-agent-loop-pairwise` is the correct packaged Houmao-owned skill
- **AND THEN** it presents itself as the restored stable pairwise planning and run-control surface rather than as the enriched v2 workflow

#### Scenario: User explicitly asks to use the stable pairwise skill for run control
- **WHEN** a user explicitly asks for `houmao-agent-loop-pairwise` to formulate a pairwise loop plan or operate one accepted run
- **THEN** `houmao-agent-loop-pairwise` is the correct packaged Houmao-owned skill
- **AND THEN** it routes the request through its authoring or operating guidance rather than claiming a new runtime control API

#### Scenario: Generic pairwise loop request does not auto-route to the stable skill
- **WHEN** a user asks generically to plan, start, inspect, or stop a pairwise loop without explicitly asking for `houmao-agent-loop-pairwise`
- **THEN** `houmao-agent-loop-pairwise` does not present itself as the default skill for that request
- **AND THEN** the request remains outside this packaged skill entrypoint unless the user later invokes the skill explicitly

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
