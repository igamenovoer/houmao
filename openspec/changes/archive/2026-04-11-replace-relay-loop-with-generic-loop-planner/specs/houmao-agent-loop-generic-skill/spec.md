## ADDED Requirements

### Requirement: Houmao provides a packaged `houmao-agent-loop-generic` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-loop-generic` under the maintained system-skill asset root.

That packaged skill SHALL use `houmao-agent-loop-generic` as both its skill name and its packaged asset directory name under `src/houmao/agents/assets/system_skills/`.

The top-level `SKILL.md` for that packaged skill SHALL describe the skill as a user-controlled generic loop graph planner and run controller rather than as a relay-only planner or a new runtime workflow engine.

That packaged skill SHALL replace the prior `houmao-agent-loop-relay` packaged skill as the current loop graph planner for relay-rooted and mixed pairwise/relay composed runs.

That packaged skill SHALL remain distinct from:

- the direct-operation skills that own messaging, gateway, mailbox, lifecycle, and inspection surfaces,
- `houmao-adv-usage-pattern`, which owns elemental pairwise and relay protocol pages,
- `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2`, which remain specialized pairwise-only planning choices.

#### Scenario: User asks for generic composed loop planning
- **WHEN** a user asks to plan a multi-agent communication graph that may contain both local-close pairwise edges and forward relay lanes
- **THEN** `houmao-agent-loop-generic` is the packaged Houmao-owned skill that owns graph decomposition and run-control planning
- **AND THEN** it does not present itself as a new transport or runtime loop engine

#### Scenario: Relay-only entrypoint is replaced
- **WHEN** a user or catalog lookup looks for the current packaged loop planner that replaced `houmao-agent-loop-relay`
- **THEN** the current packaged skill is `houmao-agent-loop-generic`
- **AND THEN** the relay-only skill name is not presented as a current installable alias

### Requirement: Generic loop authoring decomposes user intent into typed loop components
The authoring guidance in `houmao-agent-loop-generic` SHALL turn natural-language user intent into one explicit generic loop plan before run start.

Every authored generic loop plan SHALL identify at minimum:

- the designated master or root run owner,
- the allowed participant set,
- the objective,
- the typed loop components,
- the component graph or component dependency structure,
- the graph policy,
- the result-routing contract,
- the completion condition,
- the stop policy,
- the reporting contract,
- any referenced scripts and their caller or side-effect contract.

Every loop component in the plan SHALL declare at minimum:

- `component_id`,
- `component_type`,
- participating agents,
- component root, driver, or origin identity as applicable,
- downstream target or lane order,
- result-return contract,
- delegation or routing policy,
- component dependencies when the component depends on another component's result.

The supported `component_type` values SHALL include:

- `pairwise`: an immediate driver-worker local-close component that uses the elemental pairwise edge-loop protocol and returns the component result to the immediate driver,
- `relay`: a relay-rooted ordered lane that uses the elemental relay-loop protocol and returns the final result from the loop egress to the relay origin.

The authoring guidance SHALL ask for missing materially important graph, policy, or result-routing information rather than inventing free delegation, free forwarding, or hidden component dependencies.

#### Scenario: Planner creates pairwise and relay components
- **WHEN** a user describes a graph where one subtask must close back to an intermediate driver and another subtask should move forward to a downstream egress
- **THEN** the authored plan splits those parts into at least one `pairwise` component and at least one `relay` component
- **AND THEN** each component declares its own result-return contract instead of using one ambiguous graph-wide return rule

#### Scenario: Missing graph policy is not inferred
- **WHEN** a user names a finite participant set but does not authorize free delegation or free forwarding
- **THEN** the authoring guidance records restricted component policy or asks for clarification
- **AND THEN** it does not widen the plan to `delegate_any` or `forward_any`

### Requirement: Generic loop plans render typed protocol graphs
Every finalized generic loop plan produced by `houmao-agent-loop-generic` SHALL include a Mermaid fenced diagram that visualizes the final loop graph.

That diagram SHALL show at minimum:

- the user agent outside the execution loop,
- the designated master or root run owner,
- each typed loop component,
- pairwise local-close edges and their immediate result return to the driver,
- relay lane handoff edges and their final-result return to the relay origin,
- component dependencies or ordering constraints,
- where the supervision loop lives,
- where the completion condition is evaluated,
- where the stop condition is evaluated.

The graph guidance SHALL distinguish execution topology from the supervisor review loop that keeps the run alive.

The graph guidance SHALL NOT require or imply an arbitrary cyclic worker-to-worker execution graph as the default model.

#### Scenario: Mixed graph is visibly typed
- **WHEN** the authoring guidance finishes a mixed pairwise/relay generic loop plan
- **THEN** the final plan includes a Mermaid graph that labels or otherwise distinguishes pairwise components from relay components
- **AND THEN** the graph shows pairwise local-close return paths separately from relay final-egress return paths

#### Scenario: Supervision loop is separate from execution graph
- **WHEN** a reader inspects the generic loop graph
- **THEN** the graph shows where the master or root owner reviews active components and evaluates completion or stop
- **AND THEN** it does not draw the supervision loop as an arbitrary cyclic agent-to-agent message path

### Requirement: Generic loop run control keeps the user agent outside execution
The operating guidance in `houmao-agent-loop-generic` SHALL define `start`, `status`, and `stop` as control-plane interactions between the user agent and the designated master or root run owner.

The operating guidance SHALL state that the user agent is not itself a participant in pairwise receipts, relay receipts, final results, or final-result acknowledgements unless the authored plan explicitly makes a managed user-controlled agent an execution participant.

The `start` guidance SHALL send a normalized run charter to the designated master or root run owner. That charter SHALL include the plan reference, typed component summary, graph policy summary, result-routing contract, completion condition, default stop mode, and reporting contract.

After accepting a run, the designated master or root run owner SHALL be described as the owner of:

- root run state under one user-visible `run_id`,
- component dispatch,
- liveness and supervision,
- downstream pairwise and relay protocol selection per component,
- final completion evaluation,
- stop handling and stop-result summary.

The operating guidance SHALL define `status` as observational rather than as a required keepalive signal.

The operating guidance SHALL define `stop` as interrupt-first by default and SHALL allow graceful termination only when the user explicitly requests graceful stop semantics.

The operating guidance SHALL route component execution to the maintained elemental protocols:

- pairwise components use the elemental pairwise edge-loop pattern in `houmao-adv-usage-pattern`,
- relay components use the elemental relay-loop pattern in `houmao-adv-usage-pattern`.

#### Scenario: Start transfers liveness to the root owner
- **WHEN** the user agent sends a start charter for one accepted generic loop plan
- **THEN** the designated master or root run owner owns run liveness after accepting the run
- **AND THEN** the user agent is not required to keep the run alive through periodic status requests

#### Scenario: Component execution uses elemental protocols
- **WHEN** the master dispatches a `pairwise` component and a `relay` component from one generic plan
- **THEN** the pairwise component uses the elemental pairwise edge-loop protocol
- **AND THEN** the relay component uses the elemental relay-loop protocol
