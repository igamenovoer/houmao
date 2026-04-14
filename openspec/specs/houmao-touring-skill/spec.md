## Purpose
Define the packaged `houmao-touring` guided-tour system skill and its routing boundaries.
## Requirements
### Requirement: Houmao provides a packaged `houmao-touring` system skill
The system SHALL package a Houmao-owned system skill named `houmao-touring` under the maintained system-skill asset root.

That packaged skill SHALL use `houmao-touring` as both its skill name and its packaged asset directory name under `src/houmao/agents/assets/system_skills/`.

The top-level `SKILL.md` for that packaged skill SHALL describe `houmao-touring` as a guided tour for first-time or re-orienting users rather than as a direct-operation skill.

The packaged `houmao-touring` skill SHALL be manual-invocation-only. It SHALL instruct agents to use the touring skill only when the user explicitly asks for `houmao-touring` or explicitly asks for a first-time guided Houmao tour.

The packaged touring skill SHALL NOT claim ownership of the underlying direct-operation command families that it composes.

#### Scenario: User explicitly asks for the touring skill
- **WHEN** a user explicitly asks for `houmao-touring`
- **THEN** the packaged touring skill is the correct Houmao-owned entrypoint
- **AND THEN** it presents itself as a guided tour rather than as a direct command reference

#### Scenario: Ordinary direct-operation request does not auto-route to touring
- **WHEN** a user asks directly to create a specialist, launch an agent, send mail, or stop an instance without asking for the touring experience
- **THEN** `houmao-touring` does not present itself as the default skill for that request
- **AND THEN** the request remains owned by the existing direct-operation or manager skill family

### Requirement: `houmao-touring` orients from current state and supports a non-linear guided tour
The packaged `houmao-touring` skill SHALL start by orienting on current Houmao state rather than assuming the user is at the beginning of a fixed setup sequence.

That touring orientation SHALL use maintained Houmao status, list, and discovery surfaces to determine what already exists, including project overlay state, mailbox posture when relevant, reusable specialists or profiles, running managed-agent instances, and live-agent gateway or mailbox capability when relevant.

After that orientation step, the touring skill SHALL explain the current posture in plain language and SHALL offer branchable next steps rather than one mandatory next step.

At minimum, the touring branches SHALL cover:

- project overlay setup or inspection,
- project-local mailbox setup or inspection,
- specialist creation,
- optional reusable profile creation,
- managed-agent launch,
- post-launch prompt entry,
- post-launch gateway or TUI state watching,
- ordinary mailbox send or read entry,
- reminder entry,
- managed-agent stop,
- managed-agent relaunch,
- managed-agent cleanup.

After completing any branch, the touring skill SHALL allow the user to return to the current-state orientation and choose another branch, including creating additional specialists or launching additional agents.

#### Scenario: Empty workspace touring starts from project setup
- **WHEN** the guided tour finds no active project overlay, no reusable specialists, and no running managed agents
- **THEN** it explains that the workspace is still at the initial setup stage
- **AND THEN** it offers project setup as one likely next branch without claiming that the user must finish every later branch immediately

#### Scenario: Existing project with specialists can branch to more authoring or launch work
- **WHEN** the guided tour finds an existing project overlay and one or more reusable specialists
- **THEN** it explains that the user can either create another specialist, create an optional profile, or launch another agent from the current state
- **AND THEN** it does not restart the tour from project initialization as though prior state were absent

#### Scenario: Post-launch touring can return to more creation work
- **WHEN** the guided tour has already helped launch one managed agent
- **THEN** it offers post-launch branches such as prompt, watch, mail, reminder, stop, relaunch, and cleanup
- **AND THEN** it also allows the user to return to create another specialist or launch another agent instead of forcing a one-way flow

### Requirement: `houmao-touring` composes the existing Houmao skill families for execution
The packaged `houmao-touring` skill SHALL keep execution ownership on the current Houmao-owned skill families instead of restating the direct-operation command shapes in full.

At minimum, the touring skill SHALL route:

- project overlay work to `houmao-project-mgr`,
- mailbox administration work to `houmao-mailbox-mgr`,
- specialist or profile authoring plus easy-instance launch work to `houmao-specialist-mgr`,
- managed-agent prompt or mailbox-routing entry to `houmao-agent-messaging`,
- gateway watch and reminder work to `houmao-agent-gateway`,
- ordinary mailbox operations to `houmao-agent-email-comms`,
- managed-agent stop, relaunch, list, and cleanup work to `houmao-agent-instance`.

The touring skill SHALL describe those routed skills as the maintained execution surfaces for the selected branch.

The touring skill SHALL NOT reinterpret stop, relaunch, and cleanup as interchangeable actions. It SHALL explain that stop ends the live session, relaunch restarts a relaunchable managed session, and cleanup removes artifacts for stopped sessions.

#### Scenario: Prompt branch hands off to managed-agent messaging
- **WHEN** the user reaches the touring branch for sending a normal prompt to a running managed agent
- **THEN** the touring skill routes that branch through `houmao-agent-messaging`
- **AND THEN** it does not claim ownership of the lower-level prompt and gateway-delivery semantics itself

#### Scenario: Reminder and watch branches hand off to the gateway skill
- **WHEN** the user reaches the touring branch for reminder creation or gateway or TUI state watching
- **THEN** the touring skill routes that branch through `houmao-agent-gateway`
- **AND THEN** it does not flatten those gateway-specific surfaces into the touring skill itself

#### Scenario: Lifecycle follow-up distinguishes stop, relaunch, and cleanup
- **WHEN** the user reaches the touring branch for managed-agent lifecycle follow-up
- **THEN** the touring skill explains the difference between stop, relaunch, and cleanup
- **AND THEN** it routes those actions through `houmao-agent-instance` rather than treating them as one generic “manage agent” action

### Requirement: `houmao-touring` asks informative, example-driven user-input questions
When the touring skill requires user input, it SHALL ask in a first-time-user-friendly style rather than using the terse missing-input style of the direct-operation skills.

At minimum, each touring input question SHALL:

- name the requested concept in plain language,
- briefly explain why the value matters,
- provide one or more realistic examples,
- offer a recommended default or an explicit skip path when the current branch is optional.

For mailbox-oriented questions, the touring skill SHALL distinguish mailbox address from principal id, SHALL explain that mailbox local parts beginning with `HOUMAO-` under `houmao.localhost` are reserved for Houmao-owned system principals, and SHALL recommend `houmao.localhost` when the user has not already chosen a different valid mailbox domain.

For lifecycle follow-up, the touring skill SHALL explain ambiguous terms before asking for a choice, including the distinction between stopping an agent, relaunching an agent, and cleaning up stopped-session artifacts.

#### Scenario: Specialist-name question includes explanation and examples
- **WHEN** the touring skill needs a specialist name from the user
- **THEN** it asks with a short explanation of what a specialist is
- **AND THEN** it includes realistic examples such as `researcher` or `reviewer`

#### Scenario: Optional mailbox setup question includes skip guidance and reserved-prefix explanation
- **WHEN** the touring skill offers project-local mailbox setup
- **THEN** it explains what mailbox setup enables
- **AND THEN** it gives example values such as address `research@houmao.localhost` and principal id `HOUMAO-research`
- **AND THEN** it explains that `HOUMAO-research@houmao.localhost` is reserved and not the ordinary managed-agent mailbox-address pattern
- **AND THEN** it gives an explicit way to skip that branch for now

#### Scenario: Cleanup-kind question explains session versus logs
- **WHEN** the touring skill needs the user to choose a cleanup kind
- **THEN** it explains the difference between `session` cleanup and `logs` cleanup
- **AND THEN** it states that cleanup applies to stopped agents rather than live sessions

### Requirement: `houmao-touring` distinguishes mailbox-root setup from mailbox-account ownership choices
When the packaged `houmao-touring` skill offers project-local mailbox setup, it SHALL describe mailbox-root bootstrap as distinct from mailbox-account creation.

When the user's intended next step is to launch one or more specialist-backed easy instances with ordinary filesystem mailbox identities derived from managed-agent names, the touring skill SHALL explain that per-agent mailbox registration may be owned by the later `project easy instance launch` step rather than by an immediate `project mailbox register` step.

When the user instead wants a standalone shared, team, operator-facing, or otherwise manually named mailbox account that is not being created by an immediate easy-instance launch, the touring skill SHALL describe that as manual mailbox-account administration and SHALL route that work through `houmao-mailbox-mgr`.

The touring skill SHALL NOT present per-agent `project mailbox register` as a mandatory part of the common "initialize project mailbox root, then launch specialist-backed agents" flow.

#### Scenario: Guided mailbox setup for future specialist-backed launch avoids preregistering per-agent accounts
- **WHEN** the touring branch offers project-local mailbox setup
- **AND WHEN** the user is preparing to launch specialist-backed easy instances with ordinary mailbox identities such as `<agent-name>@houmao.localhost`
- **THEN** the touring skill explains that mailbox-root bootstrap and per-agent mailbox registration are separate decisions
- **AND THEN** it does not present `project mailbox register` for those same per-agent addresses as mandatory pre-launch setup

#### Scenario: Guided mailbox setup for a shared mailbox account routes manual registration explicitly
- **WHEN** the touring branch offers project-local mailbox setup
- **AND WHEN** the user wants a shared or manually named mailbox account that is not tied to an immediate specialist-backed easy launch
- **THEN** the touring skill asks for or recommends the mailbox address and principal id needed for manual registration
- **AND THEN** it routes that account-creation step through `houmao-mailbox-mgr` instead of describing it as launch-owned mailbox bootstrap

### Requirement: `houmao-touring` advises foreground-first gateway posture during guided launch branches
When the packaged `houmao-touring` skill reaches a branch that launches an agent or attaches a gateway, it SHALL advise foreground-first gateway posture for tmux-backed guided-tour flows unless the user explicitly requests background or detached gateway execution.

The touring guidance SHALL explain that the desired visible first-run topology is the managed-agent surface on tmux window `0` and, when a foreground gateway is attached, the gateway sidecar in a non-zero auxiliary tmux window.

The touring guidance SHALL distinguish a non-interactive CLI handoff that prints a `tmux attach-session` command from detached background gateway execution. It SHALL NOT tell agents to use background gateway flags merely because the current caller cannot automatically attach to tmux.

The touring guidance SHALL route detailed specialist-backed launch flag selection through `houmao-specialist-mgr` and detailed gateway lifecycle attach through `houmao-agent-gateway`, while carrying the same foreground-first and explicit-background rule into the tour branch.

#### Scenario: First-run specialist launch tour prefers foreground gateway posture
- **WHEN** the guided tour helps launch a specialist-backed easy instance
- **AND WHEN** the user has not explicitly requested background gateway execution
- **THEN** the touring branch tells the agent to omit background gateway flags
- **AND THEN** it describes the expected foreground tmux topology for an observable tour run

#### Scenario: Non-interactive handoff is not treated as background gateway execution
- **WHEN** a guided launch succeeds from a non-interactive caller and the CLI reports an attach command instead of switching into tmux
- **THEN** the touring guidance treats that as tmux handoff behavior
- **AND THEN** it does not reinterpret the session as having used detached background gateway execution unless gateway status reports that execution mode

#### Scenario: Explicit background request is honored as an override
- **WHEN** the user explicitly asks the tour to launch or attach the gateway in the background
- **THEN** the touring guidance may route to the supported background gateway flag through the owning skill
- **AND THEN** it explains that this is an explicit override from the foreground-first tour posture

#### Scenario: Gateway status clarifies current tour posture
- **WHEN** the guided tour needs to explain whether a launched agent has a foreground gateway window or detached gateway process
- **THEN** the touring guidance tells the agent to inspect supported gateway status fields such as `execution_mode` and `gateway_tmux_window_index`
- **AND THEN** it does not rely on naming conventions or assume background mode from lack of automatic tmux attachment

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

