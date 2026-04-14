## ADDED Requirements

### Requirement: `houmao-touring` offers an advanced pairwise loop creation branch
The packaged `houmao-touring` skill SHALL include an advanced-usage branch that helps guided-tour users discover pairwise agent-loop creation through the maintained pairwise loop-planning skills.

The touring skill SHALL present `houmao-agent-loop-pairwise` as the stable pairwise loop skill for authoring a pairwise loop plan and operating an accepted run through `start`, `status`, and `stop`.

The touring skill SHALL present `houmao-agent-loop-pairwise-v2` as the enriched versioned pairwise loop skill for `plan`, `initialize`, `start`, `peek`, `ping`, `pause`, `resume`, `stop`, and `hard-kill`.

The touring skill SHALL explain that the user agent remains outside the execution loop, and that the designated master owns supervision, downstream pairwise dispatch, completion evaluation, and stop handling after accepting a run.

The touring skill SHALL keep composed pairwise loop planning and run-control details in the selected pairwise loop skill. It SHALL keep elemental immediate driver-worker edge protocol guidance on `houmao-adv-usage-pattern`.

The touring skill SHALL NOT silently auto-route generic pairwise loop planning or run-control requests into either pairwise loop skill when the user has not selected that advanced branch or explicitly asked for the corresponding pairwise skill.

#### Scenario: Guided tour offers stable pairwise loop path
- **WHEN** a user is in the `houmao-touring` guided experience
- **AND WHEN** the user asks about creating an advanced pairwise agent loop
- **THEN** the touring skill offers `houmao-agent-loop-pairwise` as the stable path for pairwise loop plan authoring and `start`, `status`, and `stop` run control
- **AND THEN** it tells the caller to invoke or select `houmao-agent-loop-pairwise` for the detailed loop workflow

#### Scenario: Guided tour offers enriched v2 pairwise loop path
- **WHEN** a user is in the `houmao-touring` guided experience
- **AND WHEN** the user wants initialization, read-only peeking, ping, pause, resume, or hard-kill lifecycle controls for a pairwise loop
- **THEN** the touring skill offers `houmao-agent-loop-pairwise-v2` as the enriched versioned path
- **AND THEN** it tells the caller to invoke or select `houmao-agent-loop-pairwise-v2` for the detailed loop workflow

#### Scenario: Touring preserves pairwise skill ownership boundaries
- **WHEN** the advanced touring branch explains pairwise loop creation
- **THEN** it states that composed topology, rendered control graphs, run charters, and pairwise run-control details belong to the selected pairwise loop skill
- **AND THEN** it states that the elemental immediate driver-worker edge protocol remains on `houmao-adv-usage-pattern`
- **AND THEN** it does not restate the full pairwise mailbox, reminder, or routing-packet protocol inline

#### Scenario: Generic direct pairwise request does not activate touring or pairwise skills by accident
- **WHEN** a user asks a direct pairwise loop question without asking for the guided touring experience and without naming a pairwise loop skill
- **THEN** `houmao-touring` does not present itself as the default owner for that request
- **AND THEN** the touring guidance does not imply that either pairwise loop skill should be auto-invoked without user selection
