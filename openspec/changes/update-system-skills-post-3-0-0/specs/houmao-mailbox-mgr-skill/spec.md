# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Mailbox manager updates Stalwart boundary notes for online JMAP readiness
`houmao-mailbox-mgr` (`references/stalwart-boundary.md` and online-binding command guidance) SHALL accurately document `agents single|self mailbox online` attachment, `--trust-jmap-origin`, owner-private `--credential-source` (never inline password args), and Inbox/Sent/Archive readiness verification while keeping Stalwart server administration out of `mailbox` / `project mailbox`.

#### Scenario: Online mailbox attach enforces JMAP origin trust and owner-private credentials
- **WHEN** an operator attaches a Stalwart online mailbox via `houmao-mailbox-mgr`
- **THEN** the skill documents `--trust-jmap-origin` (required for non-default or HTTP JMAP origins), `--credential-source` file requirement, and Inbox/Sent/Archive role readiness checks

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
