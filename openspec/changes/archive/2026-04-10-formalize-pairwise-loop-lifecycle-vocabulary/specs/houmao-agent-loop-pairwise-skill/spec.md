## ADDED Requirements

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

## MODIFIED Requirements

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
