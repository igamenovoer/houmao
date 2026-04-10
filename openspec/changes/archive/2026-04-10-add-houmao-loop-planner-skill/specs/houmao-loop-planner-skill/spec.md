## ADDED Requirements

### Requirement: Houmao provides a packaged `houmao-loop-planner` system skill
The system SHALL package a Houmao-owned system skill named `houmao-loop-planner` under the maintained system-skill asset root.

That packaged skill SHALL use `houmao-loop-planner` as both its skill name and its packaged asset directory name under `src/houmao/agents/assets/system_skills/`.

The top-level `SKILL.md` for that packaged skill SHALL describe the skill as an operator-owned loop-bundle planner and handoff skill rather than as a new runtime workflow engine.

That packaged skill SHALL organize its guidance through local authoring, distribution, and handoff pages beneath the same packaged skill directory.

That packaged skill SHALL remain distinct from the loop runtime skills and the existing execution-pattern pages that it composes.

#### Scenario: User explicitly asks to author a loop bundle
- **WHEN** a user asks to create or revise a loop bundle in a user-designated directory for named Houmao agents
- **THEN** `houmao-loop-planner` is the correct packaged Houmao-owned skill
- **AND THEN** it presents itself as an operator-owned planner and handoff skill rather than as a replacement for the lower-level runtime skills

#### Scenario: User explicitly asks to prepare loop distribution material
- **WHEN** a user asks to prepare participant instructions or operator distribution guidance for a planned loop
- **THEN** `houmao-loop-planner` is the correct packaged Houmao-owned skill
- **AND THEN** it routes the request through its distribution guidance rather than claiming direct agent delivery

### Requirement: The authoring lane writes one canonical Markdown-first loop bundle
The authoring guidance in `houmao-loop-planner` SHALL write one structured loop bundle in a user-designated directory before any live run starts.

That bundle SHALL use `plan.md` as the canonical human entrypoint.

That bundle SHALL include at minimum:

- `plan.md`,
- `participants.md`,
- `execution.md`,
- `distribution.md`,
- `profile.toml`,
- `runs/charter.template.toml`.

The authoring guidance SHALL use Markdown as the primary authored format for loop meaning and operator guidance.

The authoring guidance SHALL require TOML only for `profile.toml` and `runs/charter.template.toml`.

The authoring guidance SHALL require the bundle to identify at minimum:

- the chosen loop kind,
- the designated master,
- the allowed participant set,
- the execution posture,
- the reporting posture,
- the completion behavior,
- the stop behavior.

#### Scenario: Planner creates the canonical simplified bundle layout
- **WHEN** a user asks `houmao-loop-planner` to create a new loop bundle
- **THEN** the guidance produces a bundle rooted at the user-designated directory with `plan.md` as the canonical entrypoint
- **AND THEN** the bundle includes the required participant, execution, distribution, profile, and run-template files

#### Scenario: TOML is limited to simple metadata artifacts
- **WHEN** the planner writes the canonical loop bundle
- **THEN** `profile.toml` and `runs/charter.template.toml` are the only required TOML artifacts
- **AND THEN** participant responsibilities, execution rules, and distribution guidance are written in Markdown rather than YAML or many additional TOML files

### Requirement: The authored bundle remains static and outside agent-local runtime directories
The planning guidance in `houmao-loop-planner` SHALL treat the authored loop bundle as static operator-owned material rather than as mutable runtime state.

That guidance SHALL NOT require the bundle to be stored under agent-local Houmao runtime or memory directories as part of planning.

That guidance SHALL NOT define mutable per-run ledgers, retry counters, or mailbox bookkeeping files as part of the authored bundle contract.

#### Scenario: Planner keeps authored material outside runtime scratch state
- **WHEN** a user asks `houmao-loop-planner` where to store the planned loop artifacts
- **THEN** the guidance directs the user to a user-designated directory
- **AND THEN** it does not require planning artifacts to live under agent-local Houmao runtime directories

#### Scenario: Planner does not mix profile data with mutable run ledgers
- **WHEN** a reader inspects the required bundle structure for `houmao-loop-planner`
- **THEN** the required artifacts are static planning and handoff files
- **AND THEN** the skill does not require mutable runtime ledger files inside the authored bundle

### Requirement: The bundle defines participant, execution, and distribution guidance in structured Markdown
The planning guidance in `houmao-loop-planner` SHALL define participant-local responsibilities in `participants.md`.

`participants.md` SHALL include one clearly marked section for each named participant.

Each participant section SHALL identify at minimum:

- the participant identity,
- the participant role,
- who the participant receives work from,
- who the participant reports to,
- which other agents the participant may call,
- required artifacts,
- required messages,
- escalation conditions,
- forbidden actions.

The planning guidance SHALL define shared loop behavior in `execution.md`.

`execution.md` SHALL identify at minimum:

- the loop kind,
- the execution topology summary,
- the message flow,
- the master procedure,
- the reporting posture,
- the completion behavior,
- the stop behavior.

The planning guidance SHALL define operator-managed distribution and pre-start guidance in `distribution.md`.

`distribution.md` SHALL identify at minimum:

- what the operator should send to each participant,
- what confirmations or acknowledgements to expect,
- what must be true before starting the run,
- which existing runtime skill to use next.

#### Scenario: Named participants receive explicit local contracts
- **WHEN** a loop bundle names a master and one or more additional participants
- **THEN** `participants.md` includes one section for each named participant
- **AND THEN** each participant section records the participant-local role and calling boundaries explicitly

#### Scenario: Distribution remains an operator-managed responsibility
- **WHEN** a loop bundle is prepared for later distribution
- **THEN** `distribution.md` tells the operator what to send and what to confirm before start
- **AND THEN** the guidance treats distribution as the operator's responsibility rather than as a planner-owned messaging action

### Requirement: The final bundle includes a Mermaid graph that distinguishes the operator from execution
Every finalized loop bundle produced by `houmao-loop-planner` SHALL include a Mermaid fenced diagram in `plan.md` that visualizes the top-level loop graph.

That diagram SHALL show at minimum:

- the operator outside the execution loop,
- the designated master,
- the high-level execution topology for the chosen loop kind,
- where the supervision loop lives,
- where the completion condition is evaluated,
- where the stop condition is evaluated.

#### Scenario: Plan includes a top-level Mermaid graph
- **WHEN** the planning guidance finishes one loop bundle
- **THEN** `plan.md` includes a Mermaid fenced diagram for the top-level control graph
- **AND THEN** the guidance does not rely on ASCII art as the primary graph representation

#### Scenario: Graph keeps the operator outside the execution loop
- **WHEN** a reader inspects the top-level graph in `plan.md`
- **THEN** the graph shows the operator outside the execution loop
- **AND THEN** it distinguishes the supervision loop from the execution topology itself

### Requirement: The handoff lane prepares runtime activation templates and routes by loop kind
The handoff guidance in `houmao-loop-planner` SHALL prepare one run-charter template under `runs/charter.template.toml` for later runtime activation.

That run-charter template SHALL identify at minimum:

- a run identifier placeholder,
- the profile identifier,
- the profile version,
- the chosen loop kind,
- the designated master,
- the default stop mode.

The handoff guidance SHALL route later runtime activation to an existing loop runtime skill based on the chosen loop kind.

At minimum, that routing SHALL support:

- `pairwise` -> `houmao-agent-loop-pairwise`
- `relay` -> `houmao-agent-loop-relay`

The handoff guidance SHALL NOT present `houmao-loop-planner` itself as the owner of live `start`, `status`, or `stop` operations.

#### Scenario: Pairwise bundle routes to the pairwise runtime skill
- **WHEN** a loop bundle declares `pairwise` as its loop kind
- **THEN** the handoff guidance prepares a run-charter template for that bundle
- **AND THEN** it routes later live activation to `houmao-agent-loop-pairwise`

#### Scenario: Relay bundle routes to the relay runtime skill
- **WHEN** a loop bundle declares `relay` as its loop kind
- **THEN** the handoff guidance prepares a run-charter template for that bundle
- **AND THEN** it routes later live activation to `houmao-agent-loop-relay`
