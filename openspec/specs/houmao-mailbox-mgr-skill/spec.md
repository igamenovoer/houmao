# houmao-mailbox-mgr-skill Specification

## Purpose
Define the packaged Houmao-owned mailbox-administration skill for filesystem mailbox roots, project mailbox roots, and late local managed-agent mailbox binding.

## Requirements

### Requirement: Houmao provides a packaged `houmao-mailbox-mgr` system skill
The system SHALL package a Houmao-owned system skill named `houmao-mailbox-mgr` under the maintained system-skill asset root.

That skill SHALL instruct agents and operators to handle mailbox-administration work through these maintained command surfaces:

- `houmao-mgr mailbox init|status|register|unregister|repair|cleanup`
- `houmao-mgr mailbox accounts list|get`
- `houmao-mgr mailbox messages list|get`
- `houmao-mgr project mailbox init|status|register|unregister|repair|cleanup`
- `houmao-mgr project mailbox accounts list|get`
- `houmao-mgr project mailbox messages list|get`
- `houmao-mgr agents mailbox status|register|unregister`

The top-level `SKILL.md` for that packaged skill SHALL serve as an index/router that selects local action-specific documents rather than flattening the entire workflow into one page.

That packaged skill SHALL treat these surfaces as explicitly out of scope:

- `houmao-mgr agents mail ...`
- shared gateway `/v1/mail/*` operations
- `houmao-mgr agents gateway mail-notifier ...`
- direct gateway `/v1/mail-notifier` or `/v1/wakeups`
- ad hoc filesystem editing inside mailbox roots

#### Scenario: Installed skill points the caller at maintained mailbox-admin surfaces
- **WHEN** an agent or operator opens the installed `houmao-mailbox-mgr` skill
- **THEN** the skill directs the caller to the maintained mailbox-root, project-mailbox, and late agent-binding command surfaces
- **AND THEN** it does not redirect the caller to unrelated actor-scoped mail, gateway reminder, or direct filesystem mutation paths

#### Scenario: Installed skill routes through action-specific local guidance
- **WHEN** an agent reads the installed `houmao-mailbox-mgr` skill
- **THEN** the top-level `SKILL.md` acts as an index/router for mailbox-admin actions
- **AND THEN** the detailed workflow lives in local action-specific documents rather than one flattened entry page

### Requirement: `houmao-mailbox-mgr` resolves the `houmao-mgr` launcher in the required precedence order
The packaged `houmao-mailbox-mgr` skill SHALL instruct agents to resolve the `houmao-mgr` launcher for the current workspace using this default order unless the user explicitly requests a different launcher:

1. resolve `houmao-mgr` with `command -v houmao-mgr` and use the command found on `PATH`,
2. if that lookup fails, use the uv-managed fallback `uv tool run --from houmao houmao-mgr`,
3. if the PATH lookup and uv-managed fallback do not satisfy the turn, choose an appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`.

The skill SHALL treat the `command -v houmao-mgr` result as the ordinary first-choice launcher for the current turn.

The skill SHALL treat the uv-managed fallback as the ordinary non-PATH fallback because Houmao's documented installation path uses uv tools.

The skill SHALL only probe development-project hints such as `.venv`, Pixi files, `pyproject.toml`, or `uv.lock` after PATH resolution and uv fallback do not satisfy the turn, unless the user explicitly asks for a development launcher.

The skill SHALL honor an explicit user instruction to use a specific launcher family even when a higher-priority default launcher is available.

The resolved launcher SHALL be reused for any routed mailbox-admin action selected through the packaged skill.

#### Scenario: PATH launcher is preferred before development probing
- **WHEN** `command -v houmao-mgr` succeeds in the current workspace
- **THEN** the skill tells the agent to use that PATH-resolved `houmao-mgr` command for the turn
- **AND THEN** it does not probe `.venv`, Pixi, or project-local uv launchers first

#### Scenario: uv fallback is used when PATH lookup fails
- **WHEN** `command -v houmao-mgr` fails in the current workspace
- **THEN** the skill tells the agent to try `uv tool run --from houmao houmao-mgr`
- **AND THEN** it treats that uv-managed launcher as the ordinary next fallback because Houmao is officially installed through uv tools

#### Scenario: Development launchers are later defaults, not first probes
- **WHEN** `command -v houmao-mgr` fails
- **AND WHEN** the uv-managed fallback does not satisfy the turn
- **AND WHEN** the current workspace provides development launchers such as Pixi, repo-local `.venv`, or project-local uv
- **THEN** the skill tells the agent to choose an appropriate development launcher for that workspace
- **AND THEN** it does not treat those development launchers as the default first search path

#### Scenario: Explicit user launcher choice overrides the default order
- **WHEN** the user explicitly asks to use `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, project-local `uv run houmao-mgr`, or another specific launcher
- **THEN** the skill tells the agent to honor that requested launcher
- **AND THEN** it does not replace the user-requested launcher with the default PATH-first or uv-fallback choice

### Requirement: `houmao-mailbox-mgr` routes mailbox-admin work by mailbox scope and keeps transport boundaries honest
The packaged `houmao-mailbox-mgr` skill SHALL tell the agent to recover omitted mailbox-admin inputs from the current user prompt first and from recent chat context second when those values were stated explicitly.

The skill SHALL NOT guess missing required inputs that are not explicit in current or recent conversation context.

The skill SHALL select mailbox-admin commands by mailbox scope:

- use `houmao-mgr mailbox ...` for arbitrary filesystem mailbox roots,
- use `houmao-mgr project mailbox ...` for overlay-local mailbox roots,
- use `houmao-mgr agents mailbox ...` for late filesystem mailbox binding on an existing local managed agent.

The skill SHALL describe the maintained mailbox-admin CLI in v1 as filesystem-oriented for mailbox root and registration lifecycle.

When transport-specific Stalwart context matters, the skill SHALL describe Stalwart as a mailbox transport/bootstrap boundary and SHALL NOT invent a peer `houmao-mgr mailbox ...` administration lane for Stalwart roots or accounts that does not exist.

The skill SHALL direct ordinary mailbox participation work to `houmao-agent-email-comms` and notifier-round mailbox work to `houmao-process-emails-via-gateway`.

#### Scenario: Arbitrary mailbox-root work uses the generic mailbox family
- **WHEN** the user asks to bootstrap, inspect, repair, clean, or inspect registrations under one non-project filesystem mailbox root
- **THEN** the skill directs the caller to `houmao-mgr mailbox ...`
- **AND THEN** it does not force the project overlay mailbox lane

#### Scenario: Project-local mailbox work uses the project mailbox family
- **WHEN** the user asks to manage mailbox state under the active project overlay
- **THEN** the skill directs the caller to `houmao-mgr project mailbox ...`
- **AND THEN** it does not require an explicit mailbox-root override when the project-scoped lane is the intended maintained surface

#### Scenario: Existing local managed agent mailbox attachment uses the late binding family
- **WHEN** the user asks to inspect, add, or remove filesystem mailbox support for one existing local managed agent
- **THEN** the skill directs the caller to `houmao-mgr agents mailbox ...`
- **AND THEN** it does not reinterpret that request as generic instance lifecycle or actor-scoped mailbox work

#### Scenario: Stalwart remains a documented boundary rather than a fake admin lane
- **WHEN** the current task asks about Stalwart mailbox setup or lifecycle in the context of mailbox administration
- **THEN** the skill describes Stalwart using transport/bootstrap references and current maintained runtime boundaries
- **AND THEN** it does not invent unsupported `houmao-mgr mailbox ...` root or account administration commands for the Stalwart transport

### Requirement: `houmao-mailbox-mgr` explains the ordinary mailbox-address pattern and the reserved Houmao mailbox namespace
When the packaged `houmao-mailbox-mgr` skill guides ordinary mailbox account creation or late filesystem mailbox binding, it SHALL explain the split between canonical mailbox principal id and ordinary mailbox address.

At minimum, that guidance SHALL explain:

- ordinary managed-agent principal ids use the canonical `HOUMAO-<agentname>` form,
- ordinary managed-agent mailbox addresses use `<agentname>@houmao.localhost`,
- mailbox local parts beginning with `HOUMAO-` under `houmao.localhost` are reserved for Houmao-owned system principals rather than ordinary managed-agent mailbox addresses.

When the user has not specified a mailbox domain, the skill SHALL recommend `houmao.localhost` as the ordinary default domain instead of teaching `agents.localhost` as the ordinary account-creation pattern.

When the skill uses examples for ordinary mailbox account creation, it SHALL use examples such as address `research@houmao.localhost` with principal id `HOUMAO-research`.

The skill SHALL NOT suggest `HOUMAO-<agentname>@houmao.localhost` as the ordinary managed-agent mailbox-address pattern.

#### Scenario: Generic mailbox account creation guidance recommends the Houmao domain and split identity
- **WHEN** a user asks `houmao-mailbox-mgr` how to choose mailbox identity values for one ordinary managed agent
- **AND WHEN** the user has not already supplied a full mailbox address
- **THEN** the skill recommends an address such as `research@houmao.localhost`
- **AND THEN** the same guidance distinguishes that address from principal id `HOUMAO-research`

#### Scenario: Reserved mailbox local-part rule is explained during mailbox account creation
- **WHEN** the skill gives an example or recommendation for ordinary mailbox account creation under `houmao.localhost`
- **THEN** it explains that mailbox local parts beginning with `HOUMAO-` are reserved for Houmao-owned system principals
- **AND THEN** it does not present `HOUMAO-research@houmao.localhost` as the normal mailbox-address example for an ordinary managed agent

### Requirement: `houmao-mailbox-mgr` distinguishes manual registration from launch-owned and late-binding mailbox association
The packaged `houmao-mailbox-mgr` skill SHALL describe `mailbox register` and `project mailbox register` as manual filesystem mailbox-account administration rather than as the default preparation step for every mailbox-enabled managed-agent launch.

When the user is preparing a new specialist-backed easy instance whose filesystem mailbox identity will be derived from the managed-agent instance name under the same shared mailbox root, the skill SHALL explain that launch-time mailbox bootstrap may own registration for that address and SHALL NOT present manual preregistration of the same address as the default lane.

When the user wants to add or update filesystem mailbox support for an already-running local managed agent, the skill SHALL direct that work to `agents mailbox register` rather than to `project mailbox register`.

When the user wants a standalone shared, team, integration, or operator-facing mailbox account that is not being created by immediate easy launch and is not an existing-agent late binding case, the skill SHALL continue to treat `mailbox register` or `project mailbox register` as the correct maintained lane.

#### Scenario: Same-root easy launch mailbox setup is not treated as mandatory manual preregistration
- **WHEN** the user asks `houmao-mailbox-mgr` how to prepare mailbox support for a new specialist-backed easy instance
- **AND WHEN** the intended mailbox address matches the ordinary launch-owned pattern derived from the managed-agent instance name under the same shared root
- **THEN** the skill explains that manual `project mailbox register` for that address is not the default preparatory step
- **AND THEN** it distinguishes mailbox-root bootstrap from later launch-owned registration

#### Scenario: Existing live managed agent uses the late-binding lane
- **WHEN** the user asks to add filesystem mailbox support to one already-running local managed agent
- **THEN** the skill directs the caller to `houmao-mgr agents mailbox register`
- **AND THEN** it does not reinterpret that task as generic `project mailbox register` account administration

#### Scenario: Shared mailbox account still uses manual registration
- **WHEN** the user asks to create one shared or manually named mailbox account under a mailbox root
- **AND WHEN** that account is not being created by immediate easy launch and is not an existing-agent late-binding request
- **THEN** the skill directs the caller to `houmao-mgr mailbox register` or `houmao-mgr project mailbox register` according to scope
- **AND THEN** it keeps that task inside mailbox-account administration rather than launch guidance
