# houmao-agent-loop-pairwise-skill Specification

## Purpose
TBD - created by archiving change add-houmao-agent-loop-pairwise-skill. Update Purpose after archive.
## Requirements
### Requirement: Houmao provides a packaged `houmao-agent-loop-pairwise` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-loop-pairwise` under the maintained system-skill asset root.

That packaged skill SHALL use `houmao-agent-loop-pairwise` as both its skill name and its packaged asset directory name under `src/houmao/agents/assets/system_skills/`.

The top-level `SKILL.md` for that packaged skill SHALL describe the skill as a user-controlled pairwise authoring, prestart-preparation, and run-control skill rather than as a new runtime workflow engine.

The packaged `houmao-agent-loop-pairwise` skill SHALL be manual-invocation-only. It SHALL instruct agents to use the skill only when the user explicitly asks for `houmao-agent-loop-pairwise` by name.

That packaged skill SHALL organize its guidance through local authoring, prestart, and operating pages beneath the same packaged skill directory.

That packaged skill SHALL remain distinct from the direct-operation skills and the existing `houmao-adv-usage-pattern` pattern pages that it composes.

That packaged skill SHALL NOT present itself as the default entrypoint for generic pairwise loop planning or pairwise run-control requests when the user did not explicitly invoke the skill by name.

#### Scenario: User explicitly asks to invoke the pairwise loop skill
- **WHEN** a user explicitly asks for `houmao-agent-loop-pairwise`
- **THEN** `houmao-agent-loop-pairwise` is the correct packaged Houmao-owned skill
- **AND THEN** it presents itself as a pairwise authoring, prestart, and run-control skill rather than as a replacement for the lower-level messaging, mailbox, or gateway skills

#### Scenario: User explicitly asks to use the pairwise skill for prestart or run control
- **WHEN** a user explicitly asks for `houmao-agent-loop-pairwise` to prepare, start, inspect, or stop a pairwise loop run owned by a designated master
- **THEN** `houmao-agent-loop-pairwise` is the correct packaged Houmao-owned skill
- **AND THEN** it routes the request through its authoring, prestart, or operating guidance rather than claiming a new runtime control API

#### Scenario: Generic pairwise loop request does not auto-route to the skill
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

When the authored result uses the bundle form, the bundle SHALL support explicit prestart material and standalone participant preparation briefs in addition to the canonical plan.

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

#### Scenario: Bundle plan captures structured pairwise prestart context
- **WHEN** a user asks for a larger pairwise loop that needs supporting notes or scripts
- **THEN** the authoring guidance may produce one bundle directory with `plan.md` as the canonical entrypoint
- **AND THEN** the supporting files include explicit prestart material and standalone participant preparation briefs rather than relying on unstated ambient context

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
The lifecycle guidance in `houmao-agent-loop-pairwise` SHALL define canonical operator actions for pairwise loop control while keeping the user agent outside the execution loop and placing accepted-run liveness on the designated master.

The canonical operator action vocabulary SHALL include at minimum:

- `plan`,
- `initialize`,
- `start`,
- `peek`,
- `ping`,
- `pause`,
- `resume`,
- `stop`.

The lifecycle guidance SHALL define `plan` as authoring or revising the pairwise loop contract before run start.

The lifecycle guidance SHALL define `initialize` as the preparation phase that runs before the master trigger.

That initialization phase SHALL:

- verify the participant set and authored preparation material,
- verify or enable gateway mail-notifier behavior for participating agents before the run starts,
- send one preparation email to every participating agent before the master receives the start trigger,
- keep the master trigger separate from the preparation emails,
- support default fire-and-proceed mode where the operator does not wait for readiness acknowledgement,
- support optional acknowledgement-gated mode where initialization waits for replies to the reserved operator mailbox before `start`.

The lifecycle guidance SHALL define `start` as the action that sends the normalized start trigger only to the designated master after initialization is complete.

The lifecycle guidance SHALL define `peek` as a read-only inspection action rather than as an active message send.

At minimum, `peek` SHALL support these selectors:

- `peek master`,
- `peek all`,
- `peek <agent-name>`.

The lifecycle guidance SHALL define `ping <agent-name>` as an active message to one selected participant asking for current posture or progress.

The lifecycle guidance SHALL define `pause` as suspension of the loop's wakeup mechanisms for the run rather than as mail-notifier disablement alone.

The lifecycle guidance SHALL define `resume` as restoration of those paused wakeup mechanisms.

After accepting a run, the designated master SHALL be described as the owner of:

- root run state under one user-visible `run_id`,
- supervision and retry posture,
- downstream pairwise dispatch,
- final completion evaluation,
- stop handling and stop-result summary.

The lifecycle guidance SHALL define `stop` as a master-directed termination action by default.

The lifecycle guidance SHALL NOT redefine `stop` as an implicit participant-wide broadcast.

If the skill later describes a participant-wide advisory stop broadcast, that action SHALL be documented as distinct from canonical `stop`.

The lifecycle guidance SHALL continue to state that downstream execution uses the existing pairwise edge-loop pattern rather than a new routing protocol.

#### Scenario: Initialize remains separate from start
- **WHEN** the operator asks to prepare one authored pairwise loop run before it begins
- **THEN** the lifecycle guidance routes that work through `initialize`
- **AND THEN** it keeps the later master trigger under `start` instead of collapsing both into one action

#### Scenario: Peek master stays read-only
- **WHEN** the operator asks to `peek master`
- **THEN** the lifecycle guidance treats that request as read-only inspection of master-owned run posture
- **AND THEN** it does not redefine that action as a new prompt or keepalive signal

#### Scenario: Peek all inspects participants without pinging them
- **WHEN** the operator asks to `peek all`
- **THEN** the lifecycle guidance treats that action as read-only inspection across the current participant set
- **AND THEN** it does not require sending active progress questions to every participant merely to satisfy the peek

#### Scenario: Ping selected agent is active messaging
- **WHEN** the operator asks to `ping analyst`
- **THEN** the lifecycle guidance treats that action as an active message to `analyst`
- **AND THEN** it does not present that action as equivalent to `peek analyst`

#### Scenario: Pause suspends wakeup mechanisms rather than only muting notifier
- **WHEN** the operator asks to `pause` one running pairwise loop
- **THEN** the lifecycle guidance describes the run as intentionally stalled by suspending its wakeup mechanisms
- **AND THEN** it does not describe notifier disablement alone as sufficient for canonical pause semantics

#### Scenario: Resume restores paused wakeup mechanisms
- **WHEN** the operator asks to `resume` one paused pairwise loop
- **THEN** the lifecycle guidance restores the paused wakeup mechanisms for that run
- **AND THEN** it does not treat `resume` as a synonym for starting a brand-new run

#### Scenario: Stop remains master-directed
- **WHEN** the operator asks to `stop` one active pairwise loop run
- **THEN** the lifecycle guidance routes that stop request to the designated master
- **AND THEN** it does not implicitly redefine `stop` as a participant-wide broadcast mail action

### Requirement: Pairwise loop lifecycle state names are canonical and distinct from operator actions
The lifecycle guidance in `houmao-agent-loop-pairwise` SHALL define one canonical observed state vocabulary for pairwise loop runs that is distinct from the operator action vocabulary.

That observed state vocabulary SHALL include at minimum:

- `authoring`,
- `initializing`,
- `awaiting_ack`,
- `ready`,
- `running`,
- `paused`,
- `stopping`,
- `stopped`,
- `dead`.

The lifecycle guidance SHALL describe `dead` as an observed condition of the loop rather than as an operator action.

The lifecycle guidance SHALL NOT treat these observed state names as interchangeable with the control actions used to operate the run.

#### Scenario: Acknowledgement-gated initialization exposes `awaiting_ack`
- **WHEN** the pairwise loop uses acknowledgement-gated initialization and required replies have not yet arrived
- **THEN** the lifecycle guidance describes the run as `awaiting_ack`
- **AND THEN** it does not present that condition as though the loop were already `running`

#### Scenario: Default initialization can advance to `ready` without acknowledgement waiting
- **WHEN** the pairwise loop uses default fire-and-proceed initialization and the preparation wave has been completed
- **THEN** the lifecycle guidance may describe the run as `ready`
- **AND THEN** it does not require `awaiting_ack` to be entered for that posture

#### Scenario: Dead remains an observed condition
- **WHEN** the operator or skill concludes that a pairwise loop is no longer making progress or has lost effective liveness
- **THEN** the lifecycle guidance may describe the run as `dead`
- **AND THEN** it does not present `dead` as a control action the operator can invoke

### Requirement: Pairwise authoring produces standalone participant preparation material
The authored output in `houmao-agent-loop-pairwise` SHALL define participant preparation material that can be delivered independently to each participant before the run starts.

In single-file form, the authored plan SHALL include clearly separable participant preparation sections and one clearly separable prestart section.

In bundle form, the authored output SHALL provide one standalone preparation brief for each named participant plus one shared prestart procedure.

Each participant preparation brief SHALL identify at minimum:

- the participant identity and role,
- the resources or artifacts available to that participant,
- the allowed delegation targets or allowed delegation set,
- delegation-pattern expectations for different work categories when that distinction matters,
- mailbox, reminder, receipt, or result obligations relevant to that participant,
- forbidden actions.

The participant preparation brief SHALL NOT require the participant to know, during the preparation stage, which upstream participant may later contact it or which upstream message shape may later arrive.

#### Scenario: Single-file form keeps participant preparation separable
- **WHEN** the authoring guidance produces a compact one-file pairwise plan
- **THEN** that plan includes clearly separable participant preparation material and prestart procedure
- **AND THEN** the operator can still extract each participant's preparation context without inventing missing rules

#### Scenario: Bundle form gives each participant one standalone brief
- **WHEN** the authoring guidance produces one bundle-form pairwise plan
- **THEN** the bundle includes one standalone preparation brief for each named participant
- **AND THEN** each brief remains usable without requiring the recipient to read a separate upstream-specific participant matrix first

#### Scenario: Preparation material omits upstream assumptions
- **WHEN** a participant receives its preparation brief before the run starts
- **THEN** the brief explains the participant's own resources and obligations
- **AND THEN** it does not rely on hidden assumptions about what upstream participant may later send to that participant

### Requirement: Optional downstream timeout-watch policy remains reminder-driven and non-blocking
The pairwise guidance in `houmao-agent-loop-pairwise` SHALL allow the authored plan to enable downstream timeout-watch policy for selected participants or delegation edges.

When timeout-watch policy is enabled, the guidance SHALL require the acting participant to:

- persist overdue-check state in local loop bookkeeping,
- end the current live turn after downstream dispatch and follow-up setup,
- later reopen the loop state through a reminder-driven review round,
- check mailbox first for receipts, results, or acknowledgements,
- inspect downstream state through `houmao-agent-inspect` only when the expected downstream signal is overdue.

The timeout-watch guidance SHALL NOT require the policy for all participants by default.

The timeout-watch guidance SHALL prefer one supervisor reminder per watching participant rather than one reminder per active downstream edge by default.

#### Scenario: Downstream dispatch still ends the current live turn
- **WHEN** one participant with timeout-watch policy sends work to a downstream participant
- **THEN** the guidance ends the current live turn after dispatch and follow-up setup
- **AND THEN** it does not wait in chat for downstream completion before stopping that turn

#### Scenario: Overdue downstream review is mailbox-first and uses later inspect skill peeking
- **WHEN** the expected downstream signal is overdue during a later reminder-driven review round
- **THEN** the guidance checks mailbox first
- **AND THEN** it routes later downstream peeking through `houmao-agent-inspect` only after mailbox review still shows the expected signal missing

#### Scenario: Plans without timeout-watch policy do not imply downstream peeking
- **WHEN** a pairwise plan does not enable timeout-watch policy for one participant or delegation edge
- **THEN** the guidance does not require later downstream inspection for that participant or edge
- **AND THEN** it does not invent an implicit peek obligation from the mere existence of downstream delegation
