## ADDED Requirements

### Requirement: Tmux-backed mailbox system skills resolve current mailbox bindings through a runtime-owned live resolver
For tmux-backed managed sessions, runtime-owned mailbox system skills and runtime-owned mailbox prompts SHALL resolve current mailbox bindings through a runtime-owned live mailbox binding resolver rather than relying only on the provider process's inherited mailbox env snapshot.

That live resolver SHALL:

- use the owning tmux session as the live mailbox binding source for active tmux-contained sessions,
- read only the targeted common and transport-specific mailbox binding keys needed for mailbox work,
- surface the current `AGENTSYS_MAILBOX_BINDINGS_VERSION` for mailbox refresh detection,
- avoid requiring the agent to parse raw manifest JSON or enumerate unrelated tmux env vars manually.

The existing mailbox env naming contract remains unchanged, but for tmux-backed sessions those bindings SHALL be treated as live mailbox projection data resolved through the runtime-owned resolver rather than as launch-time process env that is assumed immutable.

#### Scenario: Filesystem mailbox skill observes late-registered binding without provider relaunch
- **WHEN** a tmux-backed filesystem mailbox session receives a mailbox task after late registration updated the owning tmux session environment
- **THEN** the projected mailbox system skill resolves the current mailbox binding through the runtime-owned live resolver
- **AND THEN** the skill observes the refreshed filesystem mailbox root, mailbox directory, and mailbox-local SQLite path without requiring provider relaunch solely to refresh inherited process env
- **AND THEN** the agent does not need to reconstruct mailbox paths heuristically from stale launch-time bindings

#### Scenario: Subsequent mailbox work re-resolves after bindings-version change
- **WHEN** a tmux-backed managed session's mailbox binding changes and `AGENTSYS_MAILBOX_BINDINGS_VERSION` advances in the owning tmux session environment
- **THEN** the next mailbox-related action resolves mailbox bindings through the runtime-owned live resolver again
- **AND THEN** the mailbox skill discards cached mailbox assumptions tied to the previous bindings version

#### Scenario: Stalwart direct fallback uses the live resolver rather than stale process env
- **WHEN** a tmux-backed `stalwart` mailbox session performs direct mailbox work without a live gateway mailbox facade
- **THEN** the projected mailbox system skill resolves the current `AGENTSYS_MAILBOX_EMAIL_*` binding set through the runtime-owned live resolver
- **AND THEN** the skill uses the current session-local credential file pointer from that live binding set rather than assuming the provider process inherited a still-valid credential path at launch

### Requirement: Runtime-owned mailbox skill guidance keeps tmux integration behind the runtime-owned helper boundary
Projected mailbox system skills for tmux-backed sessions SHALL keep raw tmux integration details behind the runtime-owned live mailbox binding resolver.

The skill guidance SHALL NOT require the agent to:

- list all tmux session environment variables,
- guess which tmux session to inspect,
- parse raw `show-environment` output structure,
- or parse mailbox binding state directly from the session manifest when the runtime-owned resolver is available.

#### Scenario: Filesystem mailbox skill does not ask the agent to scrape tmux state ad hoc
- **WHEN** a tmux-backed filesystem mailbox session uses the projected mailbox system skill for mailbox work
- **THEN** that skill points the agent at the runtime-owned live mailbox binding resolver
- **AND THEN** the skill does not instruct the agent to enumerate unrelated tmux environment state or manually parse raw tmux command output
