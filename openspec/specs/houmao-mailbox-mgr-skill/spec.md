# houmao-mailbox-mgr-skill Specification

## Purpose
Define the packaged Houmao-owned mailbox-administration skill for filesystem mailbox roots, project mailbox roots, and late local managed-agent mailbox binding.
## Requirements
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

### Requirement: `houmao-mailbox-mgr` routes delivered-message reset work to clear-messages
The packaged `houmao-mailbox-mgr` skill SHALL route requests to remove all delivered messages while preserving mailbox accounts to the maintained `clear-messages` command for the selected mailbox scope.

When the task targets an arbitrary filesystem mailbox root, the skill SHALL use `houmao-mgr mailbox clear-messages`.

When the task targets the selected project overlay mailbox root, the skill SHALL use `houmao-mgr project mailbox clear-messages`.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The skill SHALL distinguish `clear-messages` from `cleanup`: `cleanup` remains for inactive or stashed registration cleanup, while `clear-messages` is the destructive delivered-message reset.

The skill SHALL NOT instruct callers to hand-edit mailbox-root files for message clearing when the maintained `clear-messages` command covers the request.

#### Scenario: Skill routes project-local message reset to project clear-messages
- **WHEN** the user asks to remove all emails from the active project mailbox root while preserving accounts
- **THEN** the skill directs the caller to `houmao-mgr project mailbox clear-messages`
- **AND THEN** it does not route the request to `project mailbox cleanup` or account unregister commands

#### Scenario: Skill routes arbitrary-root message reset to generic clear-messages
- **WHEN** the user asks to remove all emails from an explicit filesystem mailbox root while preserving accounts
- **THEN** the skill directs the caller to `houmao-mgr mailbox clear-messages --mailbox-root <path>`
- **AND THEN** it does not recommend ad hoc deletion inside the mailbox root

### Requirement: `houmao-mailbox-mgr` routes mailbox export work to the maintained export command
The packaged `houmao-mailbox-mgr` skill SHALL route requests to archive or export filesystem mailbox state to the maintained mailbox export command for the selected mailbox scope.

When the task targets an arbitrary filesystem mailbox root, the skill SHALL use `houmao-mgr mailbox export`.

When the task targets the selected project overlay mailbox root, the skill SHALL use `houmao-mgr project mailbox export`.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The skill SHALL explain that default mailbox export materializes symlinks so the archive can be used on filesystems that do not support symlinks.

The skill SHALL expose the optional `--symlink-mode preserve` choice only when the user explicitly wants symlink preservation.

The skill SHALL NOT recommend ad hoc recursive mailbox-root copying when the maintained export command covers the request.

#### Scenario: Skill routes project mailbox archive request to project export
- **WHEN** the user asks to archive the active project mailbox root
- **THEN** the skill directs the caller to `houmao-mgr project mailbox export --output-dir <dir> --all-accounts`
- **AND THEN** it explains that default export materializes symlinks

#### Scenario: Skill routes explicit mailbox-root archive request to generic export
- **WHEN** the user asks to export an explicit filesystem mailbox root at `/tmp/shared-mail`
- **THEN** the skill directs the caller to `houmao-mgr mailbox export --mailbox-root /tmp/shared-mail --output-dir <dir> --all-accounts`
- **AND THEN** it does not recommend direct filesystem copying inside the mailbox root

#### Scenario: Skill preserves selected-account export intent
- **WHEN** the user asks to export only `alice@houmao.localhost`
- **THEN** the skill preserves that account selection in the chosen command using `--address alice@houmao.localhost`
- **AND THEN** it does not replace the selected-account request with an all-account export

### Requirement: `houmao-mailbox-mgr` resolves the `houmao-mgr` launcher in the required precedence order
The packaged `houmao-mailbox-mgr` skill SHALL teach agents to resolve `houmao-mgr` for the current workspace. An explicit user choice SHALL take precedence over the default order of PATH lookup, the uv-managed fallback, and a development launcher.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The skill SHALL select mailbox-admin commands by mailbox scope:

- use `houmao-mgr mailbox ...` for arbitrary filesystem mailbox roots,
- use `houmao-mgr project mailbox ...` for overlay-local mailbox roots,
- use `houmao-mgr agents single|self ... mailbox offline ...` for late filesystem mailbox binding on an existing local managed agent,
- use `houmao-mgr agents single|self ... mailbox online {attach|detach|reconnect|refresh|status}` for late Stalwart online mailbox binding on an existing managed agent.

The skill SHALL describe `houmao-mgr mailbox ...` and `houmao-mgr project mailbox ...` as filesystem-oriented for offline mailbox roots and registrations, while supporting `agents single|self mailbox online ...` for Stalwart online binding lifecycle without inventing nonexistent `houmao-mgr mailbox ...` Stalwart root administration commands.

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
- **THEN** the skill directs the caller to `houmao-mgr agents single|self ... mailbox offline ...`
- **AND THEN** it does not reinterpret that request as generic instance lifecycle or actor-scoped mail participation

#### Scenario: Stalwart remains a documented boundary rather than a fake admin lane
- **WHEN** the current task asks about Stalwart mailbox setup or lifecycle in the context of mailbox administration
- **THEN** the skill routes live Stalwart binding lifecycle (`attach`, `detach`, `reconnect`, `refresh`, `status`) to `houmao-mgr agents single|self ... mailbox online ...` while keeping `houmao-mgr mailbox ...` and `houmao-mgr project mailbox ...` offline-only
- **AND THEN** it does not invent unsupported `houmao-mgr mailbox ...` root or account administration commands for the Stalwart transport

#### Scenario: Existing managed agent Stalwart online attachment uses mailbox online commands
- **WHEN** the current task asks to attach, detach, reconnect, refresh, or inspect Stalwart online mailbox binding for an existing managed agent
- **THEN** the skill routes to `houmao-mgr agents single|self ... mailbox online {attach|detach|reconnect|refresh|status}` with `--address`, `--login-identity`, `--credential-source`, `--jmap-url` or `--base-url`, `--trust-jmap-origin`, `--replace`, and `--expected-revision`
- **AND THEN** it still avoids inventing nonexistent `houmao-mgr mailbox ...` root or account administration commands for Stalwart

### Requirement: `houmao-mailbox-mgr` explains the ordinary mailbox-address pattern and the reserved Houmao mailbox namespace
When the packaged `houmao-mailbox-mgr` skill guides ordinary mailbox account creation or late filesystem mailbox binding, it SHALL explain the split between canonical mailbox principal id and ordinary mailbox address.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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

### Requirement: `houmao-mailbox-mgr` routes single-account message reset work to account-scoped message clear
The packaged `houmao-mailbox-mgr` skill SHALL route requests to remove delivered messages for one selected mailbox account while preserving mailbox accounts to the maintained account-scoped message clear command for the selected mailbox scope.

When the task targets one account under an arbitrary filesystem mailbox root, the skill SHALL use:

```text
houmao-mgr mailbox messages clear --address <full-address> [--mailbox-root <path>] [--dry-run] [--yes]
```

When the task targets one account under the selected project overlay mailbox root, the skill SHALL use:

```text
houmao-mgr project mailbox messages clear --address <full-address> [--dry-run] [--yes]
```

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The skill SHALL continue to route all-account delivered-message resets to `houmao-mgr mailbox clear-messages` or `houmao-mgr project mailbox clear-messages`.

The skill SHALL distinguish account-scoped message clearing from `cleanup`: `cleanup` remains for inactive or stashed registration cleanup, while `messages clear --address` removes delivered message visibility for one active account.

The skill SHALL NOT instruct callers to hand-edit mailbox-root files for single-account message clearing when the maintained account-scoped command covers the request.

#### Scenario: Skill routes project-local single-account reset to project message clear
- **WHEN** the user asks to remove all mailbox messages for `alice@houmao.localhost` in the active project mailbox root while preserving accounts
- **THEN** the skill directs the caller to `houmao-mgr project mailbox messages clear --address alice@houmao.localhost`
- **AND THEN** it does not route the request to `project mailbox clear-messages`, `project mailbox cleanup`, or account unregister commands

#### Scenario: Skill routes arbitrary-root single-account reset to generic message clear
- **WHEN** the user asks to remove all mailbox messages for `alice@houmao.localhost` under an explicit filesystem mailbox root at `/tmp/shared-mail`
- **THEN** the skill directs the caller to `houmao-mgr mailbox messages clear --mailbox-root /tmp/shared-mail --address alice@houmao.localhost`
- **AND THEN** it does not recommend ad hoc deletion inside the mailbox root

#### Scenario: Skill keeps all-account reset on clear-messages
- **WHEN** the user asks to clear all delivered messages from the selected project mailbox root while preserving accounts
- **THEN** the skill directs the caller to `houmao-mgr project mailbox clear-messages`
- **AND THEN** it does not replace the all-account reset with `project mailbox messages clear --address`

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

### Requirement: Mailbox manager updates Stalwart boundary notes for online JMAP readiness
`houmao-mailbox-mgr` (`references/stalwart-boundary.md` and online-binding command guidance) SHALL accurately document `agents single|self mailbox online` attachment, `--trust-jmap-origin`, owner-private `--credential-source` (never inline password args), and ordinary mailbox readiness under keyed or open gateways. It SHALL explain separate qualification for protected placement and keep Stalwart server administration out of `mailbox` / `project mailbox`.

#### Scenario: Online mailbox attach enforces JMAP origin trust and owner-private credentials
- **WHEN** an operator attaches a Stalwart online mailbox via `houmao-mailbox-mgr`
- **THEN** the skill documents `--trust-jmap-origin` (required for non-default or HTTP JMAP origins), `--credential-source` file requirement, and Inbox/Sent/Archive role readiness checks
- **AND THEN** it distinguishes ordinary read and submission rights from placement rights and independently authorized native filtering

### Requirement: Mailbox manager removes boilerplate and converts subcommand list to a table
`houmao-mailbox-mgr/SKILL-MAIN.md` SHALL remove its duplicated launcher block (already in `references/launcher-resolution.md`), strip Missing-Input, `houmao-cli`, and repeated Scope/Routing prose, convert the subcommand bullet list into a clean `## Subcommands` table covering all 17 executable command pages (the 16 existing offline/root pages plus `commands/agent-binding-online.md`), synchronize `manifest.toml`, and shrink `SKILL-MAIN.md` to ~95 lines.

#### Scenario: Entrypoint links references without duplicating launcher resolution
- **WHEN** a reviewer inspects `houmao-mailbox-mgr/SKILL-MAIN.md`
- **THEN** launcher precedence lives in `references/launcher-resolution.md` instead of being repeated inline, and `## Subcommands` uses a concise table covering the 16 existing offline/root commands plus `agent-binding-online`
- **AND THEN** `manifest.toml` moves `clear-messages`, `accounts-list`, `accounts-get`, `messages-list`, `messages-get`, and `messages-clear` into `commands` alongside `"agent-binding-online"`, with `aliases = ["mailbox-online=agent-binding-online"]`

### Requirement: Mailbox manager preserves offline identity, namespace reserve, and reset semantics
`houmao-mailbox-mgr` SHALL preserve `## Actor Frame Gate`, owner principal `HOUMAO-<agentname>`, `<agentname>@houmao.localhost` ordinary address, `HOUMAO-*` local-part reserve, launch-owned vs manual registration distinction, and `cleanup` vs `clear-messages` vs `messages clear --address` vs `export` symlink materialization.

#### Scenario: Offline mailbox naming and destructive cleanup preserve exact semantics
- **WHEN** an operator creates or resets an offline filesystem mailbox
- **THEN** `houmao-mailbox-mgr` distinguishes `HOUMAO-<agentname>` principal IDs from `<agentname>@houmao.localhost` addresses and keeps `clear-messages` separate from `cleanup` and `messages clear --address`
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
