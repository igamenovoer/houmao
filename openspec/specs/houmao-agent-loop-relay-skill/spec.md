# houmao-agent-loop-relay-skill Specification

## Purpose
TBD - created by archiving change add-houmao-agent-loop-relay-skill. Update Purpose after archive.
## Requirements
### Requirement: Houmao provides a packaged `houmao-agent-loop-relay` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-loop-relay` under the maintained system-skill asset root.

That packaged skill SHALL use `houmao-agent-loop-relay` as both its skill name and its packaged asset directory name under `src/houmao/agents/assets/system_skills/`.

The top-level `SKILL.md` for that packaged skill SHALL describe the skill as a user-controlled relay loop planner and run controller rather than as a new runtime workflow engine.

That packaged skill SHALL organize its guidance through local authoring and operating pages beneath the same packaged skill directory.

That packaged skill SHALL remain distinct from the direct-operation skills and the existing `houmao-adv-usage-pattern` pattern pages that it composes.

#### Scenario: User explicitly asks to plan a relay loop
- **WHEN** a user asks to formulate or revise a relay loop plan with a designated master and named Houmao agents
- **THEN** `houmao-agent-loop-relay` is the correct packaged Houmao-owned skill
- **AND THEN** it presents itself as a planner and run controller rather than as a replacement for the lower-level messaging, mailbox, or gateway skills

#### Scenario: User explicitly asks to start or stop a relay loop run
- **WHEN** a user asks to start, inspect, or stop a relay loop run owned by a designated master
- **THEN** `houmao-agent-loop-relay` is the correct packaged Houmao-owned skill
- **AND THEN** it routes the request through its operating guidance rather than claiming a new runtime control API

### Requirement: The authoring lane formulates user intent into an explicit relay loop plan
The authoring guidance in `houmao-agent-loop-relay` SHALL turn natural-language user intent into one explicit relay loop plan before run start.

That authored plan SHALL support two forms:

- one single-file Markdown plan,
- one bundle directory with `plan.md` as the canonical entrypoint plus referenced supporting Markdown files or scripts.

Every authored plan SHALL identify at minimum:

- the designated master acting as loop origin,
- the allowed participant set,
- the objective,
- the route policy,
- the relay lanes or handoff graph,
- the completion condition,
- the stop policy,
- the reporting contract,
- any referenced scripts and their caller or side-effect contract.

The authoring guidance SHALL normalize downstream forwarding authority explicitly rather than treating forwarding as free by default.

At minimum, the guidance SHALL support these route postures:

- fixed route only,
- forwarding only to named next hops or named sets,
- free forwarding within a named set,
- free forwarding to any agent.

When the plan does not explicitly authorize free forwarding, the authored result SHALL preserve that restriction rather than silently widening it.

The authored plan SHALL keep the final result anchored to the loop origin rather than treating the final result target as an implicit runtime choice.

#### Scenario: Single-file plan captures a small relay loop
- **WHEN** a user asks for a smaller relay loop that does not need many supporting files
- **THEN** the authoring guidance may produce one Markdown plan file
- **AND THEN** that file still records the master or origin, participants, route policy, completion condition, and stop policy explicitly

#### Scenario: Bundle plan captures structured relay context
- **WHEN** a user asks for a larger relay loop that needs supporting notes or scripts
- **THEN** the authoring guidance may produce one bundle directory with `plan.md` as the canonical entrypoint
- **AND THEN** the supporting files are treated as explicit references rather than as unstated ambient context

#### Scenario: Forwarding remains restricted when the user does not grant free forwarding
- **WHEN** a user's request names allowed downstream agents but does not authorize free forwarding beyond them
- **THEN** the authored plan records that restricted route policy explicitly
- **AND THEN** the master is not instructed to improvise broader forwarding authority

### Requirement: The authored plan includes a Mermaid relay graph that distinguishes routing from supervision
Every finalized relay loop plan produced by `houmao-agent-loop-relay` SHALL include a Mermaid fenced diagram that visualizes the final loop graph.

That diagram SHALL show at minimum:

- the user agent outside the execution loop,
- the designated master as loop origin and root run owner,
- the relay handoff edges between upstream and downstream agents,
- where immediate receipts flow back to the previous sender,
- where the final result returns from the loop egress to the origin,
- where the supervision loop lives,
- where the completion condition is evaluated,
- where the stop condition is evaluated.

The graph guidance SHALL treat the execution topology as forward relay routing and SHALL distinguish that topology from the supervisor review loop that keeps the run alive.

The graph guidance SHALL NOT require or imply an arbitrary cyclic worker-to-worker execution graph as the default model.

#### Scenario: Final plan includes a top-level Mermaid graph
- **WHEN** the authoring guidance finishes one relay loop plan
- **THEN** the final plan includes a Mermaid fenced code block for the top-level control graph
- **AND THEN** it does not fall back to plain-text ASCII art as the primary graph representation

#### Scenario: Diagram makes the final-result return explicit
- **WHEN** a reader inspects the final graph in the authored plan
- **THEN** the graph shows which agent acts as loop egress and where the final result returns to the origin
- **AND THEN** it distinguishes that distant return path from immediate per-hop receipt flow

### Requirement: The operating lane treats the user agent as outside the loop and places liveness on the master or origin
The operating guidance in `houmao-agent-loop-relay` SHALL define `start`, `status`, and `stop` as control-plane interactions between the user agent and the designated master acting as loop origin.

The operating guidance SHALL state that the user agent is not itself a participant in the relay execution loop.

After accepting a run, the designated master SHALL be described as the owner of:

- root run state under one user-visible `run_id`,
- supervision and retry posture,
- downstream relay dispatch,
- final completion evaluation,
- stop handling and stop-result summary.

The operating guidance SHALL define `status` as observational rather than as a required keepalive signal.

The operating guidance SHALL define `stop` as interrupt-first by default.

The operating guidance SHALL allow graceful termination only when the user explicitly requests graceful stop semantics.

The operating guidance SHALL state that downstream execution still uses the existing relay-loop pattern with `loop_id` and `handoff_id` rather than a new routing protocol.

#### Scenario: Master keeps the run alive after accepting the start request
- **WHEN** a designated master accepts one authored relay loop run
- **THEN** the skill guidance states that the master owns run liveness from that point forward
- **AND THEN** it does not require periodic status requests from the user agent to keep the run active

#### Scenario: Status request remains read-only
- **WHEN** the user agent asks the master for run status
- **THEN** the operating guidance treats that request as observation of the current run state
- **AND THEN** it does not redefine status polling as part of the master keepalive contract

#### Scenario: Default stop is interrupt-first
- **WHEN** the user agent asks to stop one active relay loop run without requesting graceful termination
- **THEN** the operating guidance defines the stop as interrupt-first
- **AND THEN** it instructs the master to stop opening new downstream work and summarize interrupted or partial results

#### Scenario: Graceful stop requires explicit user intent
- **WHEN** the user agent explicitly requests graceful termination for one active relay loop run
- **THEN** the operating guidance permits graceful stop handling for that run
- **AND THEN** it does not treat graceful drain as the default stop posture

