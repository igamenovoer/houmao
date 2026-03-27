## MODIFIED Requirements

### Requirement: Tmux-backed mailbox system skills resolve current mailbox bindings through a runtime-owned live resolver
For tmux-backed managed sessions, runtime-owned mailbox system skills and runtime-owned mailbox prompts SHALL resolve current mailbox bindings through a runtime-owned live mailbox binding resolver rather than relying only on the provider process's inherited mailbox env snapshot.

That live resolver SHALL:

- use the owning tmux session as the live mailbox binding source for active tmux-contained sessions,
- read only the targeted common and transport-specific mailbox binding keys needed for mailbox work,
- surface the current `AGENTSYS_MAILBOX_BINDINGS_VERSION` for mailbox refresh detection,
- avoid requiring the agent to parse raw manifest JSON or enumerate unrelated tmux env vars manually.

When the session also has a live attached gateway that exposes the shared `/v1/mail/*` facade, that same runtime-owned live resolver SHALL surface the current validated gateway mail-facade binding for the session. That gateway binding SHALL include the exact current `base_url` needed for attached shared-mailbox work and SHALL come from runtime-owned discovery rather than from provider-process env assumptions or tmux scraping performed by the agent.

The existing mailbox env naming contract remains unchanged, but for tmux-backed sessions those bindings SHALL be treated as live mailbox projection data resolved through the runtime-owned resolver rather than as launch-time process env that is assumed immutable.

#### Scenario: Filesystem mailbox skill observes late-registered binding without provider relaunch
- **WHEN** a tmux-backed filesystem mailbox session receives a mailbox task after late registration updated the owning tmux session environment
- **THEN** the projected mailbox system skill resolves the current mailbox binding through the runtime-owned live resolver
- **AND THEN** the skill observes the refreshed filesystem mailbox root, mailbox directory, and mailbox-local SQLite path without requiring provider relaunch solely to refresh inherited process env
- **AND THEN** the agent does not need to reconstruct mailbox paths heuristically from stale launch-time bindings

#### Scenario: Attached mailbox skill resolves the live gateway mail facade through the same resolver
- **WHEN** a tmux-backed mailbox-enabled session has a live attached gateway exposing `/v1/mail/*`
- **THEN** the runtime-owned live resolver returns both the current mailbox binding and the validated live gateway mail-facade binding for that same session
- **AND THEN** the projected mailbox system skill can obtain the exact current gateway `base_url` for attached mailbox work without scraping tmux env or guessing a default port

#### Scenario: Subsequent mailbox work re-resolves after bindings-version change
- **WHEN** a tmux-backed managed session's mailbox binding changes and `AGENTSYS_MAILBOX_BINDINGS_VERSION` advances in the owning tmux session environment
- **THEN** the next mailbox-related action resolves mailbox bindings through the runtime-owned live resolver again
- **AND THEN** the mailbox skill discards cached mailbox assumptions tied to the previous bindings version

#### Scenario: Stalwart direct fallback uses the live resolver rather than stale process env
- **WHEN** a tmux-backed `stalwart` mailbox session performs direct mailbox work without a live gateway mailbox facade
- **THEN** the projected mailbox system skill resolves the current `AGENTSYS_MAILBOX_EMAIL_*` binding set through the runtime-owned live resolver
- **AND THEN** the skill uses the current session-local credential file pointer from that live binding set rather than assuming the provider process inherited a still-valid credential path at launch
