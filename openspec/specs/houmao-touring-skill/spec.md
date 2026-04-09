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

For lifecycle follow-up, the touring skill SHALL explain ambiguous terms before asking for a choice, including the distinction between stopping an agent, relaunching an agent, and cleaning up stopped-session artifacts.

#### Scenario: Specialist-name question includes explanation and examples
- **WHEN** the touring skill needs a specialist name from the user
- **THEN** it asks with a short explanation of what a specialist is
- **AND THEN** it includes realistic examples such as `researcher` or `reviewer`

#### Scenario: Optional mailbox setup question includes skip guidance
- **WHEN** the touring skill offers project-local mailbox setup
- **THEN** it explains what mailbox setup enables
- **AND THEN** it gives example address and principal-id values and an explicit way to skip that branch for now

#### Scenario: Cleanup-kind question explains session versus logs
- **WHEN** the touring skill needs the user to choose a cleanup kind
- **THEN** it explains the difference between `session` cleanup and `logs` cleanup
- **AND THEN** it states that cleanup applies to stopped agents rather than live sessions
