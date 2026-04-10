## MODIFIED Requirements

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

### Requirement: The operating lane treats the user agent as outside the loop and places liveness on the master
The operating guidance in `houmao-agent-loop-pairwise` SHALL define `start`, `status`, and `stop` as control-plane interactions between the user agent and the designated master.

For `start`, the operating guidance SHALL define a preparation phase before the master trigger.

That preparation phase SHALL:

- verify the participant set and authored preparation material,
- verify or enable gateway mail-notifier behavior for participating agents before the run starts,
- send one preparation email to every participating agent before the master receives the start trigger,
- keep the master trigger separate from the preparation emails.

The operating guidance SHALL support two preparation postures:

- default fire-and-proceed mode where preparation email is dispatched and the operator does not wait for readiness acknowledgement,
- optional acknowledgement-gated mode where the preparation email instructs participants to reply to the reserved operator mailbox before the master trigger is sent.

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

#### Scenario: Preparation wave precedes the master trigger
- **WHEN** the user asks to start one authored pairwise loop run
- **THEN** the operating guidance sends preparation email to the participating agents before the normalized start charter is sent to the master
- **AND THEN** the master trigger remains a separate control-plane message

#### Scenario: Default preparation mode does not block on acknowledgement
- **WHEN** the authored or requested start posture uses the default preparation mode
- **THEN** the operating guidance dispatches the preparation wave without requiring readiness replies before continuing
- **AND THEN** it does not redefine acknowledgement waiting as the default start contract

#### Scenario: Acknowledgement-gated preparation waits for replies to the reserved operator mailbox
- **WHEN** the authored or requested start posture requires readiness acknowledgement
- **THEN** the operating guidance instructs participants to reply to the reserved operator mailbox
- **AND THEN** it delays the master trigger until the required replies are observed or a blocking condition is surfaced

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

## ADDED Requirements

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
