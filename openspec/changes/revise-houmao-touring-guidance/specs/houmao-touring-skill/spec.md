## MODIFIED Requirements

### Requirement: Houmao provides a packaged `houmao-touring` system skill
The system SHALL package a Houmao-owned system skill named `houmao-touring` under the maintained system-skill asset root.

That packaged skill SHALL use `houmao-touring` as both its skill name and its packaged asset directory name under `src/houmao/agents/assets/system_skills/`.

The top-level `SKILL.md` for that packaged skill SHALL describe `houmao-touring` as a guided tour for users who are not yet familiar with Houmao rather than as a direct-operation skill. That audience SHALL include first-run users, re-orienting operators, and developers who want to inspect Houmao's working logic.

The packaged `houmao-touring` skill SHALL be manual-invocation-only. It SHALL instruct agents to use the touring skill only when the user explicitly asks for `houmao-touring`, explicitly asks for a Houmao guided tour, or explicitly asks to explore Houmao by subsystem through the touring experience.

The packaged touring skill SHALL NOT claim ownership of the underlying direct-operation command families that it composes.

The packaged touring skill SHALL route concrete operation work to maintained owning skills wherever such an owner exists, and SHALL NOT duplicate detailed owner-skill workflows, command references, or option catalogs in touring content.

A bare `houmao-touring` invocation with no prompt beyond skill activation SHALL be treated as a no-prompt entrypoint. The no-prompt entrypoint SHALL scan for existing Houmao project state, infer the user's likely starting intent from that state, introduce Houmao in context, and present next-step instructions instead of asking an empty open-ended greeting.

#### Scenario: User explicitly asks for the touring skill
- **WHEN** a user explicitly asks for `houmao-touring`
- **THEN** the packaged touring skill is the correct Houmao-owned entrypoint
- **AND THEN** it presents itself as a guided tour rather than as a direct command reference

#### Scenario: User invokes touring with no prompt
- **WHEN** a user invokes bare `houmao-touring` without a concrete prompt
- **THEN** the packaged touring skill scans for existing Houmao project state
- **AND THEN** it infers the likely starting intent from the inspected state
- **AND THEN** it presents an introduction, current posture, likely intent, next choices, and required input
- **AND THEN** it does not answer only with a generic skill-activation acknowledgement or an empty "how can I help" greeting

#### Scenario: Developer asks to explore Houmao subsystem logic
- **WHEN** a user explicitly asks `houmao-touring` to explain Houmao by subsystem or component area
- **THEN** the packaged touring skill is the correct Houmao-owned entrypoint
- **AND THEN** it presents subsystem exploration rather than starting the first-agent fast path by default

#### Scenario: Ordinary direct-operation request does not auto-route to touring
- **WHEN** a user asks directly to create a specialist, launch an agent, send mail, or stop an instance without asking for the touring experience
- **THEN** `houmao-touring` does not present itself as the default skill for that request
- **AND THEN** the request remains owned by the existing direct-operation or manager skill family

## ADDED Requirements

### Requirement: `houmao-touring` presents two coverage lanes
The packaged `houmao-touring` skill SHALL present two explicit coverage lanes: fast path use cases and subsystem exploration.

Fast path use cases SHALL serve outcome-focused users who want to learn Houmao by doing useful work end to end.

Subsystem exploration SHALL serve developer-minded or component-minded users who want to understand how Houmao works by component area.

The tour SHALL keep both lanes distinct and SHALL NOT present subsystem exploration as the default outcome path.

#### Scenario: User starts the tour without choosing a lane
- **WHEN** a user starts `houmao-touring` without selecting a specific outcome or subsystem
- **THEN** the tour orients from current state
- **AND THEN** it uses inspected state to infer the likely next path
- **AND THEN** it offers that path plus fast path use cases and subsystem exploration as distinct ways to continue

#### Scenario: User asks to inspect system components
- **WHEN** a user asks to inspect how Houmao works in components
- **THEN** the tour selects subsystem exploration
- **AND THEN** it does not present the first-agent setup sequence as the only next path

### Requirement: `houmao-touring` offers three fast path use cases
The packaged `houmao-touring` skill SHALL define fast paths as use cases rather than many narrow command aliases.

At minimum, the fast path use cases SHALL be:

- Single Agent Full Run,
- Operator-Controlled Agent Team,
- Pro Agent Loop.

Single Agent Full Run SHALL guide the user toward creating and operating one fully functional managed agent, including project overlay readiness, tool and credential readiness, specialist or profile setup as needed, foreground-first launch, gateway posture, mailbox setup or binding, first prompt, inspection, memo or pages, mailbox send or read, gateway mail-notifier readiness, and reminders.

Operator-Controlled Agent Team SHALL guide the user toward creating multiple fully functional managed agents and controlling them manually as the operator, including per-agent gateway and mailbox readiness, direct prompts, operator-origin mail, inter-agent mailbox messages, notifier setup, inspection, memo or pages, reminders, and lifecycle follow-up.

Pro Agent Loop SHALL guide the user toward defining and constructing a generated loop through `houmao-agent-loop-pro`, including loop intent, participant roles, `tree-loop` or `generic-loop` topology choice, mailbox and runtime contracts, isolated workspace preparation when needed, generated artifact validation, participant launch, and generated loop operation.

The tour SHALL route concrete work inside each fast path to the maintained owning skills.

#### Scenario: User asks for one complete agent experience
- **WHEN** a user asks touring to create and operate one complete or fully functional agent
- **THEN** the tour selects Single Agent Full Run
- **AND THEN** it includes gateway, mailbox, notification, inspection, memory, and reminder surfaces as part of the intended experience instead of stopping at launch

#### Scenario: User asks for manually controlled multiple agents
- **WHEN** a user asks touring to create or control multiple agents manually
- **THEN** the tour selects Operator-Controlled Agent Team
- **AND THEN** it keeps the operator in control unless the user asks to construct a generated loop

#### Scenario: User asks for generated loop construction
- **WHEN** a user asks touring to define or construct an agent loop
- **THEN** the tour selects Pro Agent Loop when the request is schema-rich, topology-heavy, or generated-execplan oriented
- **AND THEN** it routes the detailed loop workflow through `houmao-agent-loop-pro`

### Requirement: `houmao-touring` offers subsystem exploration
The packaged `houmao-touring` skill SHALL offer subsystem exploration for users who want to understand Houmao as a system.

Subsystem exploration SHALL present a compact component map before asking which subsystem the user wants to inspect.

The component map SHALL cover, at minimum:

- Project overlay,
- Agent definition,
- Managed runtime,
- Gateway,
- Messaging,
- Mailbox,
- Memory,
- Inspection,
- Workspace,
- Loop orchestration.

For each subsystem explanation, the tour SHALL cover the subsystem boundary, required input, generated state, main operations, owning skill routes, and nearby next choices.

Subsystem exploration SHALL NOT dump low-level command reference by default. The tour SHALL use `more detail` or an equivalent user request before expanding into command examples, raw status output, advanced internals, passive server, deeper TUI tracking behavior, or deeper architecture explanation.

#### Scenario: User opens subsystem exploration
- **WHEN** a user asks `houmao-touring` to explore Houmao by subsystem
- **THEN** the tour presents a compact subsystem map
- **AND THEN** it asks which subsystem or grouped subsystem area the user wants to inspect

#### Scenario: User inspects one subsystem
- **WHEN** the user selects a subsystem such as Gateway or Mailbox
- **THEN** the tour explains what that subsystem owns, what input it needs, what Houmao generates, what operations are available, and which owning skill handles concrete work
- **AND THEN** it offers nearby next choices instead of ending with only the explanation

#### Scenario: User asks for more detail
- **WHEN** a subsystem explanation is complete
- **AND WHEN** the user asks for `more detail`
- **THEN** the tour may expand with command examples, raw evidence, advanced internals, passive server context, deeper TUI tracking behavior, or architecture detail relevant to that subsystem

### Requirement: `houmao-touring` uses compact step presentation
The packaged `houmao-touring` skill SHALL keep ordinary tour output compact by default.

At the end of each touring step, the tour SHALL present the operation result, the most critical current status, brief next-step or branch choices, and any required input needed to continue.

The packaged touring skill SHALL include presentation template examples inside the skill or a loaded subskill/branch file. These examples SHALL be illustrative response shapes, not a rigid template that every step must follow.

Presentation examples SHALL use concise language and SHALL focus on user intent, operation result, current posture, next choices, and required input instead of teaching specific command invocations.

When presenting status, operation choices, or branch choices, the tour SHALL prefer small Markdown tables over vertical lists when a table is clearer. Such tables SHALL stay scannable and SHALL use at most four columns.

The tour SHALL NOT force one rigid response template onto every step.

The tour SHALL NOT provide deep explanations, raw command output, or reference-level detail by default. It SHALL invite or honor `more detail` when the user wants expanded explanation or evidence.

The tour SHALL route to direct-operation skills where possible instead of duplicating the detailed behavior, command syntax, options, and validation rules owned by those skills.

#### Scenario: Touring step completes
- **WHEN** a touring step completes
- **THEN** the tour reports the operation result and critical current status
- **AND THEN** it presents brief next-step or branch choices and required input when more action is needed

#### Scenario: Multiple choices are available
- **WHEN** more than one next step or branch is reasonable
- **THEN** the tour presents the choices compactly
- **AND THEN** it uses a Markdown table with at most four columns when that is clearer than a list

#### Scenario: User asks for expanded explanation
- **WHEN** the user asks for `more detail`
- **THEN** the tour expands the relevant section
- **AND THEN** it may include fuller concept explanation, command examples, or raw inspection evidence

#### Scenario: Agent needs a consistent presentation shape
- **WHEN** an agent prepares a touring response for a completed step, fast path branch, or subsystem explanation
- **THEN** the packaged skill provides at least one concise presentation example that the agent can adapt
- **AND THEN** the response focuses on intent, result, status, next choices, and required input rather than low-level command invocation

#### Scenario: Concrete work belongs to another skill
- **WHEN** a selected touring path requires project setup, agent definition, launch, messaging, gateway work, mailbox work, memory, inspection, lifecycle, workspace preparation, or loop construction
- **THEN** the tour identifies the intent and routes the concrete work to the maintained owning skill
- **AND THEN** it does not restate that owning skill's full workflow or option catalog inside the touring response
