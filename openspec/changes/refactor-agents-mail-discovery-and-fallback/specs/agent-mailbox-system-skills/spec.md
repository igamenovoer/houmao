## MODIFIED Requirements

### Requirement: Mailbox system skills use a stable env-var binding contract
The system SHALL continue to publish runtime-managed mailbox binding env vars for mailbox-enabled sessions, but projected mailbox system skills SHALL consume current mailbox binding data through a manager-owned discovery command rather than by directly invoking Python module entrypoints or reconstructing transport-local paths themselves.

At minimum, the runtime SHALL continue to publish:

- `AGENTSYS_MAILBOX_TRANSPORT`,
- `AGENTSYS_MAILBOX_PRINCIPAL_ID`,
- `AGENTSYS_MAILBOX_ADDRESS`,
- `AGENTSYS_MAILBOX_BINDINGS_VERSION`,
- transport-specific mailbox binding env vars required by the selected transport.

The supported skill-facing discovery surface for current mailbox work SHALL be `houmao-mgr agents mail resolve-live`.

The existing mailbox env naming contract remains the runtime-to-manager contract, not the agent-facing contract.

#### Scenario: Filesystem mailbox skill resolves current bindings through `houmao-mgr agents mail`
- **WHEN** the runtime starts an agent session with the filesystem mailbox transport
- **THEN** the started session environment includes the common and filesystem-specific mailbox binding env vars needed by Houmao-owned discovery
- **AND THEN** the projected mailbox system skill directs the agent to `houmao-mgr agents mail resolve-live` instead of reading filesystem binding env vars directly

#### Scenario: Stalwart mailbox skill resolves current bindings through `houmao-mgr agents mail`
- **WHEN** the runtime starts an agent session with the `stalwart` mailbox transport
- **THEN** the started session environment includes the common and email-specific mailbox binding env vars needed by Houmao-owned discovery
- **AND THEN** the projected mailbox system skill directs the agent to `houmao-mgr agents mail resolve-live` instead of direct Python-module or env-var-specific transport discovery

### Requirement: Tmux-backed mailbox system skills resolve current mailbox bindings through a runtime-owned live resolver
For tmux-backed managed sessions, projected mailbox system skills SHALL resolve current mailbox bindings through the runtime-owned live resolver exposed by `houmao-mgr agents mail resolve-live` rather than relying on the provider process's inherited mailbox env snapshot or a direct Python-module entrypoint.

That live resolver SHALL:

- support same-session discovery when selectors are omitted inside the owning managed tmux session,
- use `AGENTSYS_MANIFEST_PATH` as the primary current-session discovery source with `AGENTSYS_AGENT_ID` as fallback,
- read only the targeted common and transport-specific mailbox binding keys needed for mailbox work,
- surface the current `AGENTSYS_MAILBOX_BINDINGS_VERSION` for mailbox refresh detection,
- surface the current validated gateway mail-facade binding for the session when a live gateway is attached,
- avoid requiring the agent to parse raw manifest JSON or enumerate unrelated tmux env vars manually.

When a live gateway is attached, the resolver SHALL return the exact current `gateway.base_url` needed for attached shared-mailbox work.

#### Scenario: Filesystem mailbox skill observes late-registered binding without provider relaunch
- **WHEN** a tmux-backed filesystem mailbox session receives a mailbox task after late registration updated the owning tmux session environment
- **THEN** the projected mailbox system skill resolves the current mailbox binding through `houmao-mgr agents mail resolve-live`
- **AND THEN** the skill observes the refreshed filesystem mailbox binding without requiring provider relaunch solely to refresh inherited process env

#### Scenario: Attached mailbox skill resolves the live gateway mail facade through `houmao-mgr agents mail`
- **WHEN** a tmux-backed mailbox-enabled session has a live attached gateway exposing `/v1/mail/*`
- **THEN** `houmao-mgr agents mail resolve-live` returns both the current mailbox binding and the validated live gateway mail-facade binding for that same session
- **AND THEN** the projected mailbox system skill can obtain the exact current gateway `base_url` for attached mailbox work without scraping tmux env or guessing a default port

#### Scenario: Stalwart no-gateway mailbox work uses the live resolver instead of stale process env
- **WHEN** a tmux-backed `stalwart` mailbox session performs mailbox work without a live gateway mailbox facade
- **THEN** the projected mailbox system skill resolves the current binding set through `houmao-mgr agents mail resolve-live`
- **AND THEN** the skill uses the current mailbox binding returned by that manager-owned discovery surface rather than assuming the provider process inherited still-current values at launch

### Requirement: Runtime-owned mailbox skill guidance keeps tmux integration behind the runtime-owned helper boundary
Projected mailbox system skills for tmux-backed sessions SHALL keep raw tmux integration details behind the runtime-owned helper boundary exposed through `houmao-mgr`.

The skill guidance SHALL NOT require the agent to:

- list all tmux session environment variables,
- guess which tmux session to inspect,
- parse raw `show-environment` output structure,
- parse mailbox binding state directly from the session manifest when the runtime-owned helper is available,
- invoke `python -m houmao.agents.mailbox_runtime_support ...` directly as part of ordinary mailbox work.

#### Scenario: Filesystem mailbox skill does not ask the agent to scrape tmux state or call a Python module directly
- **WHEN** a tmux-backed filesystem mailbox session uses the projected mailbox system skill for mailbox work
- **THEN** that skill points the agent at `houmao-mgr agents mail resolve-live`
- **AND THEN** the skill does not instruct the agent to enumerate unrelated tmux environment state or invoke a direct Python-module resolver entrypoint

### Requirement: Projected mailbox system skills keep routine attached-session actions on the shared gateway facade
When a live loopback gateway exposes the shared `/v1/mail/*` mailbox surface for a mailbox-enabled session, the projected mailbox system skills SHALL treat that shared gateway facade as the default routine action surface for ordinary mailbox work.

Projected mailbox system skills for both filesystem and `stalwart` transports SHALL present that default structurally: resolve current mailbox state through `houmao-mgr agents mail resolve-live`, use gateway HTTP when it is available, and fall back to `houmao-mgr agents mail ...` when it is not.

For this change, ordinary mailbox work includes:

- checking unread mail,
- sending one new message,
- replying to one existing message,
- marking one processed message read.

When projected mailbox skills expose thin tmux-session-local shell helpers, those helpers SHALL delegate only to gateway HTTP or `houmao-mgr agents mail ...` rather than to direct Python-module entrypoints or mailbox-owned scripts.

For attached filesystem sessions, projected mailbox system skills SHALL NOT present direct mailbox-owned Python scripts as the ordinary no-gateway fallback path for those routine actions.

For attached `stalwart` sessions, projected mailbox system skills SHALL NOT present direct Python-module mailbox discovery as the ordinary no-gateway fallback path for those routine actions.

#### Scenario: Attached mailbox session uses the shared gateway facade when available
- **WHEN** a mailbox-enabled session has a live attached gateway exposing `/v1/mail/*`
- **THEN** the projected mailbox system skill resolves the current gateway endpoint through `houmao-mgr agents mail resolve-live`
- **AND THEN** the skill directs the agent to use gateway HTTP for the shared mailbox operation instead of reasoning about transport details directly

#### Scenario: Mailbox session without gateway falls back to `houmao-mgr agents mail`
- **WHEN** a mailbox-enabled session has no live shared gateway mailbox facade
- **THEN** the projected mailbox system skill directs the agent to use `houmao-mgr agents mail ...` for routine mailbox work
- **AND THEN** the fallback remains manager-owned and transport-neutral from the agent's perspective

#### Scenario: Thin shell helpers stay wrappers over supported surfaces
- **WHEN** a projected mailbox skill provides a shell helper for tmux-session-local mailbox work
- **THEN** that helper wraps `houmao-mgr agents mail resolve-live`, gateway HTTP, or `houmao-mgr agents mail ...`
- **AND THEN** it does not become a second canonical mailbox contract with independent transport logic

### Requirement: Filesystem mailbox system skills instruct agents to consult shared mailbox rules first
The system SHALL require the projected filesystem mailbox system skill to present shared mailbox `rules/` as mailbox-local policy guidance for agents rather than as an executable mutation contract.

That policy guidance MAY include markdown instructions about:

- message formatting,
- local reply or subject conventions,
- mailbox-local etiquette,
- other presentation or workflow hints specific to that mailbox.

The skill SHALL NOT present mailbox `rules/` as requiring the agent to execute mailbox-owned Python helper scripts for ordinary send, reply, check, or mark-read work.

#### Scenario: Filesystem mailbox skill treats mailbox-local rules as policy guidance
- **WHEN** an agent uses the projected filesystem mailbox system skill for mailbox reads or writes
- **THEN** that skill may direct the agent to consult shared mailbox `rules/` for mailbox-local policy guidance
- **AND THEN** the skill does not treat mailbox `rules/` as an executable mutation contract for ordinary mailbox operations

### Requirement: Filesystem mailbox system skills instruct agents to mark processed mail read explicitly
The system SHALL require the projected filesystem mailbox system skill to distinguish between discovering unread mail and marking a message read after processing.

That skill SHALL instruct agents to mark a message read only after the agent has actually processed that message successfully.

When the agent is using gateway HTTP, the skill SHALL direct the agent to `POST /v1/mail/state`.

When the agent is using the manager-owned fallback path, the skill SHALL direct the agent to `houmao-mgr agents mail mark-read`.

The skill SHALL NOT instruct agents to mark a message read merely because unread mail was detected or because a reminder prompt mentioned the message.

#### Scenario: Agent marks processed message read through the selected manager or gateway surface
- **WHEN** an agent finishes processing an unread mailbox message successfully
- **THEN** the projected mailbox system skill instructs the agent to mark that message read through `POST /v1/mail/state` when gateway HTTP is in use or `houmao-mgr agents mail mark-read` when the manager fallback path is in use
- **AND THEN** the agent does not treat message discovery or reminder prompts as implicit read-state mutation

## REMOVED Requirements

### Requirement: Runtime-owned mailbox commands rely on projected mailbox system skills
**Reason**: Manager-owned mailbox command surfaces are being refactored to execute mailbox work directly instead of depending on agent-prompt mediation for ordinary mailbox follow-up.
**Migration**: Use gateway HTTP for attached-session mailbox work when a live gateway is available, or use `houmao-mgr agents mail ...` as the supported manager-owned fallback surface.

### Requirement: Filesystem mailbox system skills direct sensitive operations to shared scripts
**Reason**: Mailbox-owned Python scripts are no longer part of the ordinary agent-facing execution contract.
**Migration**: Use gateway HTTP when available, or use `houmao-mgr agents mail ...` for routine send, reply, check, and mark-read work instead of invoking mailbox-owned scripts directly.

### Requirement: Filesystem mailbox system skills surface Python helper dependencies
**Reason**: Ordinary mailbox work should not require agents to inspect or manage Python helper dependencies.
**Migration**: Treat helper dependencies as Houmao implementation detail or compatibility detail and use `houmao-mgr agents mail ...` as the supported mailbox execution surface.

### Requirement: Filesystem mailbox system skills may suggest optional header helper scripts
**Reason**: Formatting and normalization guidance belongs in mailbox-local markdown policy or Houmao-owned execution behavior, not in mailbox-owned helper invocation advice for ordinary agent turns.
**Migration**: Put mailbox-local formatting conventions in markdown policy under `rules/` and keep message normalization inside Houmao-owned execution paths where needed.
