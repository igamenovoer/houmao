## ADDED Requirements

### Requirement: Mailbox system skills use a stable resolver contract for current mailbox discovery
The system SHALL expose current mailbox discovery for projected mailbox system skills through `houmao-mgr agents mail resolve-live` rather than through mailbox-specific `AGENTSYS_MAILBOX_*` env bindings.

The resolver output SHALL provide the current mailbox binding in structured form, including the selected transport, principal id, mailbox address, transport-specific actionable fields derived from the durable session mailbox binding, and any validated live gateway mail-facade binding for the same session.

Projected mailbox system skills SHALL treat that resolver output as the supported mailbox-discovery contract and SHALL NOT require mailbox-specific shell export steps before ordinary mailbox work.

#### Scenario: Filesystem mailbox skill resolves current mailbox state through the manager-owned resolver
- **WHEN** the runtime starts an agent session with the filesystem mailbox transport
- **THEN** the projected mailbox system skill directs the agent to `houmao-mgr agents mail resolve-live`
- **AND THEN** the returned structured mailbox binding includes the current derived filesystem mailbox state needed for mailbox work without relying on `AGENTSYS_MAILBOX_*`

#### Scenario: Stalwart mailbox skill resolves current mailbox state through the manager-owned resolver
- **WHEN** the runtime starts an agent session with the `stalwart` mailbox transport
- **THEN** the projected mailbox system skill directs the agent to `houmao-mgr agents mail resolve-live`
- **AND THEN** the returned structured mailbox binding includes the current derived Stalwart mailbox state needed for mailbox work without relying on `AGENTSYS_MAILBOX_*`

## MODIFIED Requirements

### Requirement: Tmux-backed mailbox system skills resolve current mailbox bindings through a runtime-owned live resolver
For tmux-backed managed sessions, projected mailbox system skills SHALL resolve current mailbox bindings through the runtime-owned live resolver exposed by `houmao-mgr agents mail resolve-live` rather than relying on the provider process's inherited mailbox env snapshot, mailbox-specific tmux env, or a direct Python-module entrypoint.

That live resolver SHALL:

- support same-session discovery when selectors are omitted inside the owning managed tmux session,
- use `AGENTSYS_MANIFEST_PATH` as the primary current-session discovery source with `AGENTSYS_AGENT_ID` as fallback,
- derive current mailbox state from the durable session mailbox binding instead of from targeted mailbox tmux env keys,
- surface transport-specific actionable mailbox fields needed for current mailbox work,
- surface the current validated gateway mail-facade binding for the session when a live gateway is attached,
- avoid requiring the agent to parse raw manifest JSON or enumerate unrelated tmux env vars manually.

When a live gateway is attached, the resolver SHALL return the exact current `gateway.base_url` needed for attached shared-mailbox work.

#### Scenario: Filesystem mailbox skill observes a late-registered binding without provider relaunch
- **WHEN** a tmux-backed filesystem mailbox session receives a mailbox task after late registration updated the durable session mailbox binding
- **THEN** the projected mailbox system skill resolves the current mailbox binding through `houmao-mgr agents mail resolve-live`
- **AND THEN** the skill observes the refreshed filesystem mailbox state without requiring provider relaunch or mailbox-specific tmux env refresh

#### Scenario: Attached mailbox skill resolves the live gateway mail facade through `houmao-mgr agents mail`
- **WHEN** a tmux-backed mailbox-enabled session has a live attached gateway exposing `/v1/mail/*`
- **THEN** `houmao-mgr agents mail resolve-live` returns both the current mailbox binding and the validated live gateway mail-facade binding for that same session
- **AND THEN** the projected mailbox system skill can obtain the exact current gateway `base_url` for attached mailbox work without scraping tmux env or guessing a default port

#### Scenario: Stalwart no-gateway mailbox work uses the live resolver instead of stale process env
- **WHEN** a tmux-backed `stalwart` mailbox session performs mailbox work without a live gateway mailbox facade
- **THEN** the projected mailbox system skill resolves the current binding set through `houmao-mgr agents mail resolve-live`
- **AND THEN** the skill uses the current mailbox binding returned by that manager-owned discovery surface rather than assuming the provider process inherited still-current values at launch

## REMOVED Requirements

### Requirement: Mailbox system skills use a stable env-var binding contract
**Reason**: Mailbox-specific env bindings are no longer part of the supported mailbox discovery contract for runtime-owned skills or manager-owned mailbox workflows.
**Migration**: Resolve current mailbox state through `houmao-mgr agents mail resolve-live` structured output instead of reading or depending on `AGENTSYS_MAILBOX_*`.

### Requirement: Filesystem mailbox binding env vars are refreshable on demand
**Reason**: The system no longer maintains a mailbox env-refresh contract for active sessions.
**Migration**: Late mailbox mutation updates durable mailbox binding state, and subsequent mailbox work re-resolves current filesystem mailbox data through the manager-owned resolver.
