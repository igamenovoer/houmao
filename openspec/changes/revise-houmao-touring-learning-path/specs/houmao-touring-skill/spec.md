## ADDED Requirements

### Requirement: `houmao-touring` presents a three-stage first-user learning path
The packaged `houmao-touring` skill SHALL organize guided-tour guidance into three learning stages: beginner, intermediate, and advanced.

The beginner stage SHALL focus on basic agent creation and communication. It SHALL cover, at minimum, tool selection, credential readiness, project overlay basics, mailbox subsystem basics, specialist creation, optional easy launch profile creation, managed-agent launch, and talking to the launched agent.

The intermediate stage SHALL focus on live operation and manual coordination after the user has a useful agent context. It SHALL cover, at minimum, managed-agent memo and pages, ordinary direct prompts, inter-agent mailbox messaging, operator-origin mail or prompt injection through mail, gateway mail-notifier posture, gateway-notified mail rounds, and inter-agent inspection.

The advanced stage SHALL focus on composed multi-agent systems. It SHALL cover, at minimum, loop authoring and operation through `houmao-agent-loop-lite` and `houmao-agent-loop-pro`, tree-loop and generic-loop mode selection inside pro, and isolated multi-agent workspace management through `houmao-utils-workspace-mgr`.

The touring skill SHALL present these stages as learning progression and navigation aids rather than as install sets, complete function categories, or a full system-skill catalog.

#### Scenario: First-time user sees beginner guidance first
- **WHEN** a first-time user starts `houmao-touring` in a blank or minimally configured workspace
- **THEN** the tour presents beginner-stage guidance before intermediate or advanced guidance
- **AND THEN** the tour frames beginner as the path to create one usable managed agent and talk to it

#### Scenario: Running-agent user can move to intermediate guidance
- **WHEN** the tour detects or recently helped create at least one running managed agent
- **THEN** the tour offers intermediate-stage next actions for live operation, memory, messaging, notifier, mailbox, and inspection workflows
- **AND THEN** it does not require the user to inspect the full advanced feature surface

#### Scenario: Team coordination intent can move to advanced guidance
- **WHEN** the user asks to coordinate multiple agents, generate a loop, or isolate agent workspaces
- **THEN** the tour offers advanced-stage guidance
- **AND THEN** it routes loop work to `houmao-agent-loop-lite` or `houmao-agent-loop-pro` and workspace work to `houmao-utils-workspace-mgr`

### Requirement: `houmao-touring` uses stage-aware next touring actions
After orientation and after each completed branch, the packaged `houmao-touring` skill SHALL offer next touring actions that match the user's current stage and inspected state.

Beginner next actions SHALL prefer the next useful onboarding step, such as choosing a tool, preparing credentials, creating a specialist, creating an optional easy profile, initializing mailbox basics, launching an agent, or sending the first prompt.

Intermediate next actions SHALL prefer live operation and manual coordination, such as sending another prompt, inspecting live or mailbox state, adding or reading memo context, sending mailbox work, enabling or checking mail-notifier posture, processing a notifier-reported mail round, launching a second agent, or coordinating agents manually.

Advanced next actions SHALL prefer composed coordination setup, such as preparing isolated workspaces, choosing lite or pro loop authoring, choosing tree-loop or generic-loop mode inside pro, generating or validating loop artifacts, launching participants, or operating the generated loop.

The touring skill SHALL NOT use generic "show everything" or broad catalog enumeration as the normal next action for a first-time user.

#### Scenario: Beginner branch finishes with beginner and intermediate options
- **WHEN** a beginner branch launches the user's first managed agent
- **THEN** the next touring actions include talking to the agent, inspecting what is running, adding memo context, sending mail to the agent, or launching a second agent
- **AND THEN** advanced loop and workspace actions are not presented as the primary follow-up unless the user asks for team coordination

#### Scenario: Intermediate branch finishes with coordination options
- **WHEN** an intermediate branch completes an inspection, memo, mailbox, notifier, or live-operation workflow
- **THEN** the next touring actions include continuing live operation, inspecting mailbox or gateway state, coordinating another agent manually, or moving to advanced loops when repeated coordination is emerging

#### Scenario: Advanced branch finishes with loop or workspace options
- **WHEN** an advanced branch prepares workspace or loop context
- **THEN** the next touring actions include validating the workspace or loop plan, launching participants, operating the loop, or returning to live inspection

## MODIFIED Requirements

### Requirement: `houmao-touring` orients from current state and supports a non-linear guided tour
The packaged `houmao-touring` skill SHALL start by orienting on current Houmao state rather than assuming the user is at the beginning of a fixed setup sequence.

That touring orientation SHALL use maintained Houmao status, list, and discovery surfaces to determine what already exists, including project overlay state, mailbox posture when relevant, reusable specialists or profiles, running managed-agent instances, managed-agent memory posture when relevant, and live-agent gateway or mailbox capability when relevant.

After that orientation step, the touring skill SHALL explain the current posture in plain language and SHALL offer branchable next steps organized by beginner, intermediate, or advanced learning stage rather than one mandatory next step.

At minimum, the beginner-stage touring branches SHALL cover:

- project overlay setup or inspection,
- project-local mailbox basics,
- tool selection,
- credential readiness,
- specialist creation,
- optional reusable easy profile creation,
- managed-agent launch,
- first direct prompt or conversation with the launched agent.

At minimum, the intermediate-stage touring branches SHALL cover:

- managed-agent memo or pages orientation,
- post-launch prompt entry,
- inter-agent mailbox send or read entry,
- operator-origin mail or prompt injection through mail,
- post-launch gateway, TUI, mailbox, logs, or turn-state inspection,
- gateway mail-notifier status or enablement,
- one gateway-notified mail processing round,
- reminder entry,
- manual coordination across more than one running agent.

At minimum, the advanced-stage touring branches SHALL cover:

- lightweight loop authoring or generated-loop operation through `houmao-agent-loop-lite`,
- schema-rich loop authoring or generated-loop operation through `houmao-agent-loop-pro`,
- tree-loop and generic-loop mode selection inside `houmao-agent-loop-pro`,
- isolated multi-agent workspace planning or execution through `houmao-utils-workspace-mgr`.

After completing any branch, the touring skill SHALL allow the user to return to the current-state orientation and choose another stage-appropriate branch, including creating additional specialists, launching additional agents, coordinating running agents, or moving into advanced loop and workspace workflows when the user asks for that level of orchestration.

#### Scenario: Empty workspace touring starts from beginner setup
- **WHEN** the guided tour finds no active project overlay, no reusable specialists, and no running managed agents
- **THEN** it explains that the workspace is still at the beginner setup stage
- **AND THEN** it offers beginner setup actions without claiming that the user must immediately learn intermediate or advanced workflows

#### Scenario: Existing project with specialists can branch to authoring or launch work
- **WHEN** the guided tour finds an existing project overlay and one or more reusable specialists
- **THEN** it explains that the user can either create another specialist, create an optional easy profile, or launch an agent from the current beginner-stage foundation
- **AND THEN** it does not restart the tour from project initialization as though prior state were absent

#### Scenario: Post-launch touring can move to intermediate operation
- **WHEN** the guided tour has already helped launch one managed agent
- **THEN** it offers intermediate branches such as prompt, memo, inspect, mail, notifier, reminder, and manual multi-agent coordination
- **AND THEN** it also allows the user to return to create another specialist or launch another agent instead of forcing a one-way flow

### Requirement: `houmao-touring` composes the existing Houmao skill families for execution
The packaged `houmao-touring` skill SHALL keep execution ownership on the current Houmao-owned skill families instead of restating the direct-operation command shapes in full.

At minimum, the touring skill SHALL route:

- project overlay work to `houmao-project-mgr`,
- mailbox administration work to `houmao-mailbox-mgr`,
- credential readiness and credential content work to `houmao-credential-mgr` when credential mutation or inspection is needed,
- specialist, easy profile, raw profile, create-agent-fast-forward, and specialist-backed easy-instance launch work to `houmao-agent-definition`,
- generic managed-agent inspection, live screen watching, mailbox-posture inspection, logs, turn-state evidence, and runtime artifact inspection to `houmao-agent-inspect`,
- managed-agent prompt, interrupt, raw input, or mailbox-routing entry to `houmao-agent-messaging`,
- gateway lifecycle, gateway watch, gateway mail-notifier, and reminder work to `houmao-agent-gateway`,
- ordinary mailbox send, read, reply, post, or archive follow-up to `houmao-agent-email-comms`,
- one gateway-notified open-mail processing round with prompt-provided gateway base URL to `houmao-process-emails-via-gateway`,
- managed-agent memo, pages, or launch-profile memo-seed work to `houmao-memory-mgr`,
- lightweight Markdown/direct-SQL loop authoring, validation, and generated loop execution to `houmao-agent-loop-lite`,
- schema-rich loop authoring, generated execplan validation, topology-heavy planning, and generated loop execution to `houmao-agent-loop-pro`,
- isolated multi-agent workspace planning or execution to `houmao-utils-workspace-mgr`,
- managed-agent stop, relaunch, list, join/adopt, and cleanup work to `houmao-agent-instance`.

The touring skill SHALL describe those routed skills as the maintained execution surfaces for the selected branch.

The touring skill SHALL NOT reinterpret stop, relaunch, and cleanup as interchangeable actions. It SHALL explain that stop ends the live session, relaunch restarts a relaunchable managed session, and cleanup removes artifacts for stopped sessions.

#### Scenario: Prompt branch hands off to managed-agent messaging
- **WHEN** the user reaches the touring branch for sending a normal prompt to a running managed agent
- **THEN** the touring skill routes that branch through `houmao-agent-messaging`
- **AND THEN** it does not claim ownership of the lower-level prompt and gateway-delivery semantics itself

#### Scenario: Mail prompt-injection branch hands off to mailbox operations
- **WHEN** the user reaches an intermediate touring branch for operator-origin mail, prompt injection through mail, or inter-agent mailbox messaging
- **THEN** the touring skill routes ordinary mailbox operations through `houmao-agent-email-comms`
- **AND THEN** it routes one notifier-reported open-mail processing round through `houmao-process-emails-via-gateway` when the round context provides the gateway base URL

#### Scenario: Memo branch hands off to memory manager
- **WHEN** the user reaches an intermediate touring branch for managed-agent memo, pages, or profile memo seed work
- **THEN** the touring skill routes that branch through `houmao-memory-mgr`
- **AND THEN** it does not treat memo content as mailbox state, gateway reminder state, or arbitrary runtime bookkeeping

#### Scenario: Reminder and watch branches hand off to the gateway skill
- **WHEN** the user reaches the touring branch for reminder creation or gateway or TUI state watching
- **THEN** the touring skill routes that branch through `houmao-agent-gateway`
- **AND THEN** it does not flatten those gateway-specific surfaces into the touring skill itself

#### Scenario: Advanced workspace branch hands off to workspace manager
- **WHEN** the user reaches an advanced touring branch for isolated multi-agent workspace planning or execution
- **THEN** the touring skill routes that branch through `houmao-utils-workspace-mgr`
- **AND THEN** it does not launch agents as part of workspace preparation unless the user later selects a launch branch owned by the launch or instance skill

#### Scenario: Lifecycle follow-up distinguishes stop, relaunch, and cleanup
- **WHEN** the user reaches the touring branch for managed-agent lifecycle follow-up
- **THEN** the touring skill explains the difference between stop, relaunch, and cleanup
- **AND THEN** it routes those actions through `houmao-agent-instance` rather than treating them as one generic "manage agent" action

### Requirement: `houmao-touring` orient branch uses an explicit posture-to-branch routing matrix
The packaged `houmao-touring` skill orient branch SHALL include an explicit routing table that maps inspected workspace posture to stage-aware next touring actions.

That routing table SHALL at minimum cover the postures "no overlay and no specialists and no running agents", "overlay exists without specialists", "specialists exist without running agents", "one or more running managed agents", "mailbox and notifier-capable running agent", "stopped or relaunchable managed agents", and "multi-agent or team-coordination workspace".

The orient branch SHALL use that table as the source of truth for offering next actions rather than re-deriving routing in free prose on each turn.

The offered next actions SHALL remain offers rather than mandates; the orient branch SHALL NOT force the user into exactly one row entry when more than one is reasonable for the inspected posture.

#### Scenario: Empty workspace posture offers beginner setup actions
- **WHEN** the orient branch inspects a workspace with no project overlay, no reusable specialists, and no running managed agents
- **THEN** it uses the routing table to offer beginner quickstart and explicit project/mailbox setup actions
- **AND THEN** it explains that those actions are the path toward one launched managed agent

#### Scenario: Post-launch posture offers intermediate operation actions
- **WHEN** the orient branch inspects a workspace with one or more running managed agents
- **THEN** it uses the routing table to offer intermediate actions such as talk, inspect, memo, mailbox, notifier, reminder, and manual coordination
- **AND THEN** it does not treat setup branches as the primary next step unless the user asks to create or launch more agents

#### Scenario: Multi-agent workspace posture offers advanced coordination when relevant
- **WHEN** the orient branch inspects a workspace with multiple running agents or the user asks for team coordination
- **THEN** it uses the routing table to offer advanced loop and isolated workspace actions alongside relevant intermediate live-operation actions
- **AND THEN** it does not require the user to choose advanced guidance when ordinary manual coordination is enough

### Requirement: `houmao-touring` advanced-usage branch teaches advanced orchestration rather than enumerating all features
The packaged `houmao-touring` advanced guidance SHALL teach advanced orchestration concepts rather than enumerate the broader Houmao feature surface as a flat catalog.

The advanced guidance SHALL include entries for:

- lightweight generated loops through `houmao-agent-loop-lite`,
- schema-rich generated loops through `houmao-agent-loop-pro`,
- tree-loop and generic-loop mode selection inside `houmao-agent-loop-pro`,
- isolated multi-agent workspace planning and execution through `houmao-utils-workspace-mgr`.

The advanced guidance MAY mention `houmao-adv-usage-pattern` when the user wants elemental mailbox/gateway coordination patterns before generated loops, but it SHALL keep elemental pattern detail on that owning skill.

The advanced guidance SHALL NOT present unrelated utility workflows as part of first-user touring merely because they are packaged system skills.

The advanced guidance SHALL NOT mark any advanced orchestration entry as the recommended, preferred, primary, or default advanced feature unless the user's stated goal clearly selects that entry.

The advanced guidance SHALL NOT restate generated loop templates, topology contracts, workspace execution rules, mailbox result protocol, reminder protocol, memory file layouts, or credential lifecycle details inline; those belong to the selected owning skill.

#### Scenario: Advanced guidance focuses on loop and workspace orchestration
- **WHEN** the user reaches advanced touring guidance
- **THEN** the touring skill presents loop-lite, loop-pro, pro tree/generic modes, and isolated workspace management as the advanced orchestration subjects
- **AND THEN** it does not present the full packaged skill catalog as the advanced tour

#### Scenario: Advanced guidance routes each entry to its owning skill
- **WHEN** the user picks one advanced orchestration entry
- **THEN** the touring skill tells the agent to invoke or select the owning skill named in that entry
- **AND THEN** it does not attempt to restate the detailed workflow for that entry inline

#### Scenario: Utility skills remain outside normal touring unless relevant
- **WHEN** a packaged utility skill is not part of first-user agent creation, live operation, manual coordination, loop authoring, or isolated workspace management
- **THEN** `houmao-touring` does not include it in the normal beginner, intermediate, or advanced learning path
- **AND THEN** users can still reach that utility through direct skill invocation or system-skills reference documentation

## REMOVED Requirements

### Requirement: `houmao-touring` offers an advanced pairwise loop creation branch
**Reason**: The pairwise and generic loop package names are retired as current touring choices. Touring now routes current loop work through `houmao-agent-loop-lite` and `houmao-agent-loop-pro`, with tree-loop and generic-loop as mode choices inside pro.

**Migration**: Use the staged advanced guidance and the existing current-loop requirements that route lightweight Markdown/direct-SQL loops to `houmao-agent-loop-lite` and schema-rich topology-heavy loops to `houmao-agent-loop-pro`.

### Requirement: Touring presents tree loop and generic loop families
**Reason**: This requirement preserves retired pairwise-named skill handles as current routing identities, which conflicts with the current catalog and the newer requirement that touring SHALL NOT enumerate retired pairwise or generic loop packages as current choices.

**Migration**: Keep tree-loop and generic-loop wording only as mode choices inside `houmao-agent-loop-pro`; do not route users to retired pairwise or generic loop skill packages from touring.
