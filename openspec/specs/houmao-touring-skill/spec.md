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

### Requirement: `houmao-touring` presents a state-adaptive welcome message

The packaged `houmao-touring` skill SHALL present a welcome message that adapts to the inspected current Houmao state at the start of the guided tour.

When the inspected workspace has no project overlay, no reusable specialists, and no running managed agents, the touring skill SHALL present the full welcome text that introduces Houmao in plain language and names the typical initial setup path.

When the inspected workspace already has any of those state components, the touring skill SHALL present a short acknowledgement in place of the full welcome, immediately followed by the current-state orientation and the offered next branches, so that the user is not pushed back to the beginning of setup.

The touring skill SHALL NOT repeat the full welcome text on every turn, and SHALL NOT present the full welcome when the recent conversation has already covered it.

#### Scenario: Blank-slate tour shows the full welcome

- **WHEN** a user starts the `houmao-touring` guided tour in a workspace with no project overlay, no reusable specialists, and no running managed agents
- **THEN** the touring skill presents the full welcome text, including the plain-language description of Houmao and the typical initial setup path
- **AND THEN** it continues with current-state orientation and the offered next branches

#### Scenario: Workspace with existing state shows short acknowledgement instead of the full welcome

- **WHEN** a user starts the `houmao-touring` guided tour in a workspace that already has a project overlay, reusable specialists, or running managed agents
- **THEN** the touring skill presents a short acknowledgement instead of the full welcome text
- **AND THEN** it presents the current-state orientation and the offered next branches first
- **AND THEN** it does not push the user back to the initial setup sequence

#### Scenario: Welcome is not repeated when the recent conversation already covered it

- **WHEN** the recent conversation already included the welcome text for `houmao-touring`
- **THEN** the touring skill does not re-emit the full welcome text on the next turn
- **AND THEN** it proceeds with current-state orientation and branch selection

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

### Requirement: `houmao-touring` offers a quickstart branch that detects available host CLI tools

The packaged `houmao-touring` skill SHALL include a quickstart branch that helps a user reach one running managed agent with the minimum number of decisions.

The quickstart branch SHALL detect which supported tool CLIs are available on the host by running a presence check such as `command -v <tool>` for each tool adapter supported by the packaged Houmao distribution.

The quickstart branch SHALL list the detected tools to the user without priority, without ordering that implies recommendation, and without marking any detected tool as the default or preferred tool.

When no supported tool CLI is detected on the host, the quickstart branch SHALL explain which tool CLIs Houmao supports and SHALL NOT attempt to launch a managed agent.

The quickstart branch SHALL route the actual specialist authoring, credential attachment, and easy-instance launch work through the maintained downstream skills (`houmao-specialist-mgr` and related) rather than restating their command shapes.

#### Scenario: Host has one supported tool CLI

- **WHEN** the quickstart branch detects exactly one supported tool CLI on the host
- **THEN** it lists that tool and explains the user can launch a minimum-viable specialist with it
- **AND THEN** it routes specialist authoring and launch through `houmao-specialist-mgr`

#### Scenario: Host has multiple supported tool CLIs

- **WHEN** the quickstart branch detects more than one supported tool CLI on the host
- **THEN** it lists the detected tools without priority, without ordering that implies recommendation, and without naming any of them as the default
- **AND THEN** it asks the user to pick one before proceeding

#### Scenario: Host has no supported tool CLI

- **WHEN** the quickstart branch detects no supported tool CLI on the host
- **THEN** it explains which tool CLIs Houmao supports
- **AND THEN** it does not attempt to launch a managed agent in that turn

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

### Requirement: `houmao-touring` ships a self-contained concepts reference

The packaged `houmao-touring` skill SHALL ship a concepts reference file at `references/concepts.md` inside its packaged asset directory.

That concepts reference SHALL be a compact self-contained glossary of the vocabulary the tour uses, including at minimum `specialist`, `easy profile`, `launch profile`, `managed agent`, `recipe`, `tool adapter`, `project overlay`, `gateway`, `gateway sidecar`, `mailbox root`, `mailbox account`, `principal id`, `user agent`, `master`, `loop plan`, `relaunch`, and `cleanup`.

Each glossary entry SHALL be short (roughly one to three sentences) and SHALL cross-reference the owning Houmao-owned skill when such a skill exists, so that deeper detail remains on the owning skill rather than duplicated in the glossary.

The concepts reference SHALL be usable as a standalone file without reading any other file in the repository.

The touring `SKILL.md` and touring branch pages SHALL be allowed to cite `references/concepts.md` for vocabulary grounding.

#### Scenario: Concepts reference is present inside the packaged asset directory

- **WHEN** the packaged `houmao-touring` skill is installed on a user workspace
- **THEN** `references/concepts.md` is present inside the installed asset directory
- **AND THEN** it is reachable without depending on any file outside the packaged asset directory

#### Scenario: Concepts reference covers the minimum vocabulary

- **WHEN** the tour cites the concepts reference during an explanation
- **THEN** the reference defines `specialist`, `easy profile`, `launch profile`, `managed agent`, `recipe`, `tool adapter`, `project overlay`, `gateway`, `gateway sidecar`, `mailbox root`, `mailbox account`, `principal id`, `user agent`, `master`, `loop plan`, `relaunch`, and `cleanup`
- **AND THEN** each entry stays compact and cross-references the owning skill when applicable

### Requirement: `houmao-touring` content is self-contained inside its packaged asset directory

All content that the packaged `houmao-touring` skill reads, links, or instructs the agent to read SHALL live inside `src/houmao/agents/assets/system_skills/houmao-touring/`.

The touring skill SHALL NOT reference paths under the development-only parts of the repository (including but not limited to `examples/`, `docs/`, `magic-context/`, and `openspec/`) because those paths are not present in the pypi-distributed wheel.

The touring skill SHALL NOT reference files that only exist in the source repository checkout and therefore disappear after `pip install`.

This self-containment rule SHALL apply to `SKILL.md`, every file under `branches/`, every file under `references/`, and any future file added to the packaged asset directory.

#### Scenario: Touring content does not reference repo-only paths

- **WHEN** a reviewer audits the packaged `houmao-touring` skill content
- **THEN** no reference, link, or instructional sentence points at a path outside `src/houmao/agents/assets/system_skills/houmao-touring/`
- **AND THEN** the skill remains fully usable against a pypi-installed Houmao distribution

#### Scenario: Installed touring skill works without the source repository

- **WHEN** the `houmao-touring` skill is invoked on a host that only has the pypi-installed Houmao distribution and does not have a clone of the Houmao source repository
- **THEN** every branch page and reference cited by `SKILL.md` is reachable
- **AND THEN** the user-facing tour experience is identical to running the tour from a source checkout

### Requirement: Touring system-input questions label required and optional values
When `houmao-touring` asks the user for Houmao system setup or lifecycle input, it SHALL identify required values separately from optional values or skip paths.

The touring question SHALL keep first-time-user guidance, including plain-language concept names, short explanations, realistic examples, and recommended defaults where useful.

This requirement SHALL apply to project overlay setup, mailbox setup, specialist or profile setup, managed-agent launch, post-launch gateway or mailbox setup, lifecycle follow-up, and cleanup choices.

This requirement SHALL NOT apply to questions about the user's task content or domain goals unless the question is specifically about Houmao runtime behavior.

#### Scenario: Project setup question labels required and optional values
- **WHEN** the guided tour asks the user to create or select a Houmao project overlay
- **THEN** the question labels the required project location or confirmation separately from optional naming, discovery-mode, or skip choices
- **AND THEN** it still explains why the project overlay matters

#### Scenario: Optional branch shows skip path as optional
- **WHEN** the guided tour offers an optional mailbox, profile, gateway, or post-launch branch
- **THEN** the question labels the branch-specific blocking values as required only if the user chooses that branch
- **AND THEN** it labels the skip path or default as optional

#### Scenario: Lifecycle choice explains terms and labels inputs
- **WHEN** the guided tour asks whether to stop, relaunch, clean up, or inspect a managed agent
- **THEN** it explains the difference between the lifecycle choices
- **AND THEN** it labels the required target selector and selected lifecycle action separately from optional modifiers

### Requirement: Touring presents pro as the current loop path
The touring skill SHALL present `houmao-agent-loop-pro` as the current advanced loop authoring and execution path.

The touring skill SHALL NOT enumerate retired pairwise or generic loop packages as current loop choices.

#### Scenario: Touring user asks about advanced loops
- **WHEN** a user asks touring for advanced loop creation or loop operation guidance
- **THEN** touring identifies `houmao-agent-loop-pro` as the current loop skill
- **AND THEN** it describes tree-loop and generic-loop as mode choices inside pro

### Requirement: Touring presents lite and pro as current loop branches
The `houmao-touring` skill SHALL present `houmao-agent-loop-lite` and `houmao-agent-loop-pro` as the current maintained loop-authoring branches.

Touring SHALL route lightweight Markdown/direct-SQL/no-harness loop requests to `houmao-agent-loop-lite`.

Touring SHALL route schema-rich, topology-heavy, harness-backed, validation-heavy, or complex generated-execplan requests to `houmao-agent-loop-pro`.

Touring SHALL NOT route current loop planning or generated loop run-control requests to retired pairwise or generic loop packages.

#### Scenario: Touring user asks for the simplest loop system
- **WHEN** a touring user asks for a simple loop definition with Markdown and direct SQLite
- **THEN** touring identifies `houmao-agent-loop-lite` as the current branch
- **AND THEN** it explains that lite omits generated harness and docs layers

#### Scenario: Touring user asks for complex generated execplans
- **WHEN** a touring user asks for generated topology contracts, harness validation, or schema-typed mail
- **THEN** touring identifies `houmao-agent-loop-pro` as the current branch
- **AND THEN** it does not present lite as equivalent for that work
