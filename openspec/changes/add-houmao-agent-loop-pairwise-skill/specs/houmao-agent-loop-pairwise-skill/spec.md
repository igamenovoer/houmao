## ADDED Requirements

### Requirement: Houmao provides a packaged `houmao-agent-loop-pairwise` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-loop-pairwise` under the maintained system-skill asset root.

That packaged skill SHALL use `houmao-agent-loop-pairwise` as both its skill name and its packaged asset directory name under `src/houmao/agents/assets/system_skills/`.

The top-level `SKILL.md` for that packaged skill SHALL describe the skill as a user-controlled pairwise loop planner and run controller rather than as a new runtime workflow engine.

That packaged skill SHALL organize its guidance through local authoring and operating pages beneath the same packaged skill directory.

That packaged skill SHALL remain distinct from the direct-operation skills and the existing `houmao-adv-usage-pattern` pattern pages that it composes.

#### Scenario: User explicitly asks to plan a pairwise loop
- **WHEN** a user asks to formulate or revise a pairwise loop plan with a designated master and named Houmao agents
- **THEN** `houmao-agent-loop-pairwise` is the correct packaged Houmao-owned skill
- **AND THEN** it presents itself as a planner and run controller rather than as a replacement for the lower-level messaging, mailbox, or gateway skills

#### Scenario: User explicitly asks to start or stop a pairwise loop run
- **WHEN** a user asks to start, inspect, or stop a pairwise loop run owned by a designated master
- **THEN** `houmao-agent-loop-pairwise` is the correct packaged Houmao-owned skill
- **AND THEN** it routes the request through its operating guidance rather than claiming a new runtime control API

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

#### Scenario: Bundle plan captures structured loop context
- **WHEN** a user asks for a larger pairwise loop that needs supporting notes or scripts
- **THEN** the authoring guidance may produce one bundle directory with `plan.md` as the canonical entrypoint
- **AND THEN** the supporting files are treated as explicit references rather than as unstated ambient context

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
The operating guidance in `houmao-agent-loop-pairwise` SHALL define `start`, `status`, and `stop` as control-plane interactions between the user agent and the designated master.

The operating guidance SHALL state that the user agent is not itself a participant in the pairwise execution loop.

After accepting a run, the designated master SHALL be described as the owner of:

- root run state under one user-visible `run_id`,
- supervision and retry posture,
- downstream pairwise dispatch,
- final completion evaluation,
- stop handling and stop-result summary.

The operating guidance SHALL define `status` as observational rather than as a required keepalive signal.

The operating guidance SHALL define `stop` as interrupt-first by default.

The operating guidance SHALL allow graceful termination only when the user explicitly requests graceful stop semantics.

The operating guidance SHALL state that downstream execution still uses the existing pairwise edge-loop pattern rather than a new routing protocol.

#### Scenario: Master keeps the run alive after accepting the start request
- **WHEN** a designated master accepts one authored pairwise loop run
- **THEN** the skill guidance states that the master owns run liveness from that point forward
- **AND THEN** it does not require periodic status requests from the user agent to keep the run active

#### Scenario: Status request remains read-only
- **WHEN** the user agent asks the master for run status
- **THEN** the operating guidance treats that request as observation of the current run state
- **AND THEN** it does not redefine status polling as part of the master keepalive contract

#### Scenario: Default stop is interrupt-first
- **WHEN** the user agent asks to stop one active pairwise loop run without requesting graceful termination
- **THEN** the operating guidance defines the stop as interrupt-first
- **AND THEN** it instructs the master to stop opening new downstream work and summarize interrupted or partial results

#### Scenario: Graceful stop requires explicit user intent
- **WHEN** the user agent explicitly requests graceful termination for one active pairwise loop run
- **THEN** the operating guidance permits graceful stop handling for that run
- **AND THEN** it does not treat graceful drain as the default stop posture
