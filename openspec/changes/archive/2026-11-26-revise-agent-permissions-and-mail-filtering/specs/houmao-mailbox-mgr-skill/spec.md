# Mailbox Manager Skill Delta

## ADDED Requirements

### Requirement: Mailbox manager guides ordinary Stalwart attachment on open and keyed gateways

The Mailbox Manager skill SHALL guide authorized callers to attach a ready Stalwart account through an open or keyed gateway using owner-private mailbox credentials. It SHALL explain that first-key enrollment preserves the existing binding and that provider account provisioning and rule administration use the provider's separate management surfaces.

#### Scenario: The gateway is already keyed when the owner attaches Stalwart

- **WHEN** an operator wants to attach a ready Stalwart account to an already-keyed gateway
- **THEN** the guidance uses the maintained `houmao-mgr agents single|self ... mailbox online attach` command with the selected account, JMAP origin, and owner-private mailbox credential
- **AND THEN** the caller uses an explicit target in admin posture or verified self in agent posture
- **AND THEN** it explains that ordinary attachment requires mailbox-level readiness and that protected filtering qualifies separately

#### Scenario: The owner enrolls the first key after attaching Stalwart

- **WHEN** an operator enrolls the first key on a gateway that already has a ready Stalwart binding
- **THEN** the guidance explains that the existing binding remains usable through the keyed gateway under the applicable authorization checks
- **AND THEN** it retains the existing offline mailbox slot and agent body

### Requirement: Mailbox manager guides qualification for protected filtering

The Mailbox Manager skill SHALL explain the backend requirements for protected filtering on the selected binding. It SHALL explain that the backend files matching new deliveries directly into Archive using placement and rule authority independent of the gateway runtime.

#### Scenario: An operator qualifies a provider mailbox for protected filtering

- **WHEN** an operator asks to enable protected filtering on a Stalwart binding
- **THEN** the guidance directs the operator to the trusted provider management path to verify native direct-to-Archive delivery at the selected account and isolation from ordinary gateway credentials
- **AND THEN** it keeps native provider administration separate from both the Houmao filesystem root commands and the ordinary online binding lifecycle

#### Scenario: An operator qualifies a filesystem mailbox for protected filtering

- **WHEN** an operator asks to enable protected filtering on a filesystem mailbox
- **THEN** the guidance requires a trusted registry or equivalent isolated writer with exclusive write access to the authoritative mailbox state and control over peer access
- **AND THEN** it explains that the trusted writer enforces placement for the registered mailbox while its gateway is absent

#### Scenario: The backend cannot qualify for protected filtering

- **WHEN** an operator uses a shared writable filesystem or an online provider that lacks native direct-to-Archive delivery or independent placement authority
- **THEN** the guidance identifies protected filtering as unsupported and retains the existing ordinary mailbox routes under their applicable checks

### Requirement: Mailbox manager guides independent policy application and verification

The Mailbox Manager skill SHALL direct owners to the trusted backend or its management connector for signing authority and outcome verification. It SHALL describe the gateway's policy apply endpoint as an authorized relay for a signed rule update to the exact mailbox.

#### Scenario: An owner applies rules and verifies the committed revision

- **WHEN** an owner requests a blocklist update on a qualified mailbox binding
- **THEN** the guidance describes the independent owner signature for the exact operation, backend, binding or registration, expected revision, operation ID, and mail rules
- **AND THEN** it directs authorized callers to `POST /v1/mail/{channel}/policy/apply` for gateway relay or the trusted authority for direct submission
- **AND THEN** it directs the owner to verify the applied revision and outcome through independently authorized backend access

#### Scenario: The caller holds only gateway administration or mailbox credentials

- **WHEN** a caller asks whether ordinary credentials can configure protected placement
- **THEN** the guidance explains that the trusted backend requires independent owner proof for the rule update
- **AND THEN** it reserves rule and placement administration for the trusted authority on that binding

## MODIFIED Requirements

### Requirement: Mailbox manager updates Stalwart boundary notes for online JMAP readiness
`houmao-mailbox-mgr` (`references/stalwart-boundary.md` and online-binding command guidance) SHALL accurately document `agents single|self mailbox online` attachment, `--trust-jmap-origin`, owner-private `--credential-source` (never inline password args), and ordinary mailbox readiness under keyed or open gateways. It SHALL explain separate qualification for protected placement and keep Stalwart server administration out of `mailbox` / `project mailbox`.

#### Scenario: Online mailbox attach enforces JMAP origin trust and owner-private credentials
- **WHEN** an operator attaches a Stalwart online mailbox via `houmao-mailbox-mgr`
- **THEN** the skill documents `--trust-jmap-origin` (required for non-default or HTTP JMAP origins), `--credential-source` file requirement, and Inbox/Sent/Archive role readiness checks
- **AND THEN** it distinguishes ordinary read and submission rights from placement rights and independently authorized native filtering

### Requirement: Houmao provides a packaged `houmao-mailbox-mgr` system skill
The system SHALL package a Houmao-owned system skill named `houmao-mailbox-mgr` under the maintained system-skill asset root.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

That skill SHALL instruct agents and operators to handle mailbox-administration work through these maintained command surfaces:

- `houmao-mgr mailbox init|status|register|unregister|repair|cleanup|clear-messages|export`
- `houmao-mgr mailbox accounts list|get`
- `houmao-mgr mailbox messages list|get`
- `houmao-mgr project mailbox init|status|register|unregister|repair|cleanup|clear-messages|export`
- `houmao-mgr project mailbox accounts list|get`
- `houmao-mgr project mailbox messages list|get`
- `houmao-mgr agents single|self ... mailbox offline {status|join|leave}`
- `houmao-mgr agents single|self ... mailbox online {attach|detach|reconnect|refresh|status}`

The packaged `SKILL-MAIN.md` for that routine SHALL serve as an index/router that selects local action-specific documents rather than flattening the entire workflow into one page.

That packaged skill SHALL treat these surfaces as explicitly out of scope:

- `houmao-mgr agents mail ...`
- ordinary per-message gateway `/v1/mail/*` operations
- `houmao-mgr agents gateway mail-notifier ...`
- direct gateway `/v1/mail-notifier` or `/v1/wakeups`
- ad hoc filesystem editing inside mailbox roots

#### Scenario: Installed skill points the caller at maintained mailbox-admin surfaces
- **WHEN** an agent or operator opens the installed `houmao-mailbox-mgr` skill
- **THEN** the skill directs the caller to the maintained mailbox-root, project-mailbox, and late agent-binding command surfaces
- **AND THEN** it does not redirect the caller to unrelated actor-scoped mail, gateway reminder, or direct filesystem mutation paths

#### Scenario: Installed skill routes through action-specific local guidance
- **WHEN** an agent reads the installed `houmao-mailbox-mgr` skill
- **THEN** the packaged `SKILL-MAIN.md` acts as an index/router for mailbox-admin actions
- **AND THEN** the detailed workflow lives in local action-specific documents rather than one flattened entry page

### Requirement: `houmao-mailbox-mgr` distinguishes manual registration from launch-owned and late-binding mailbox association
The packaged `houmao-mailbox-mgr` skill SHALL describe `mailbox register` and `project mailbox register` as manual filesystem mailbox-account administration rather than as the default preparation step for every mailbox-enabled managed-agent launch.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

When the user is preparing a new specialist-backed easy instance whose filesystem mailbox identity will be derived from the managed-agent instance name under the same shared mailbox root, the skill SHALL explain that launch-time mailbox bootstrap may own registration for that address and SHALL NOT present manual preregistration of the same address as the default lane.

When the user wants to add or update filesystem mailbox support for an already-running local managed agent, the skill SHALL direct that work to scoped `agents single|self ... mailbox offline join` rather than to `project mailbox register`.

When the user wants a standalone shared, team, integration, or operator-facing mailbox account that is not being created by immediate easy launch and is not an existing-agent late binding case, the skill SHALL continue to treat `mailbox register` or `project mailbox register` as the correct maintained lane.

#### Scenario: Same-root easy launch mailbox setup is not treated as mandatory manual preregistration
- **WHEN** the user asks `houmao-mailbox-mgr` how to prepare mailbox support for a new specialist-backed easy instance
- **AND WHEN** the intended mailbox address matches the ordinary launch-owned pattern derived from the managed-agent instance name under the same shared root
- **THEN** the skill explains that manual `project mailbox register` for that address is not the default preparatory step
- **AND THEN** it distinguishes mailbox-root bootstrap from later launch-owned registration

#### Scenario: Existing live managed agent uses the late-binding lane
- **WHEN** the user asks to add filesystem mailbox support to one already-running local managed agent
- **THEN** the skill directs the caller to `houmao-mgr agents single|self ... mailbox offline join`
- **AND THEN** it does not reinterpret that task as generic `project mailbox register` account administration

#### Scenario: Shared mailbox account still uses manual registration
- **WHEN** the user asks to create one shared or manually named mailbox account under a mailbox root
- **AND WHEN** that account is not being created by immediate easy launch and is not an existing-agent late-binding request
- **THEN** the skill directs the caller to `houmao-mgr mailbox register` or `houmao-mgr project mailbox register` according to scope
- **AND THEN** it keeps that task inside mailbox-account administration rather than launch guidance

### Requirement: `houmao-mailbox-mgr` uses direct command snippets for mailbox commands
The packaged `houmao-mailbox-mgr` skill SHALL document supported mailbox administration commands as direct fenced `bash` snippets or equivalent explicit command shapes.

Covered command families SHALL include shared mailbox commands, project mailbox commands, project mailbox account/message commands, and managed-agent mailbox binding commands.

The skill SHALL keep transport explanation and mailbox workflow guidance in skill text, but executable command shapes SHALL be shown directly.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The skill SHALL NOT reference `houmao-mgr internals command-templates`, command-template ids, template blockers, or command-template support when explaining mailbox administration commands.

#### Scenario: Managed-agent mailbox register uses direct scoped command shape
- **WHEN** a user asks the skill to register a filesystem mailbox binding for one selected managed agent
- **THEN** the skill guidance shows a direct command under `houmao-mgr agents single --agent-name <agent-name> mailbox offline join ...` or `houmao-mgr agents single --agent-id <agent-id> mailbox offline join ...`
- **AND THEN** it does not direct the agent to render a managed-agent mailbox command-template id
