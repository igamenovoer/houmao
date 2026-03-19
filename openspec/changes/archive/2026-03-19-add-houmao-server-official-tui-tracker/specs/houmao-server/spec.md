## ADDED Requirements

### Requirement: `houmao-server` separates direct watch observation from CAO-compatible control delegation
`houmao-server` SHALL keep its live watch and parsing path separate from any CAO-compatible control delegation path.

For live TUI parsing and continuous state tracking, `houmao-server` SHALL observe tmux and process state directly.

For CAO-compatible create, mutate, or control routes that remain delegated in v1, `houmao-server` MAY still use its child CAO adapter.

#### Scenario: Delegated control does not make CAO the watch authority
- **WHEN** `houmao-server` delegates a CAO-compatible control route such as session creation or input delivery to the child CAO adapter
- **THEN** that delegation does not make child CAO the authoritative parser or live-state source for the watched session
- **AND THEN** the watch plane continues to use direct tmux and process observation

### Requirement: `houmao-server` seeds known-session tracking from server-owned registrations
`houmao-server` SHALL rebuild and refresh the known-session registry for this capability from server-managed session registration records for the sessions this server owns.

It SHALL enrich those registration records with manifest-backed metadata and live tmux facts when available.

Shared live-agent registry records MAY be consulted as compatibility evidence or alias enrichment, but they SHALL NOT by themselves become the primary authority that admits a session into background watch management.

#### Scenario: Startup rebuild uses server-owned registration and live tmux
- **WHEN** `houmao-server` restarts and finds a server-managed registration record whose tmux session is still live
- **THEN** it rebuilds the known-session entry from that registration
- **AND THEN** the resulting background watch worker resumes from that rebuilt entry instead of waiting for child-CAO polling

#### Scenario: Shared registry evidence alone does not create a watched session
- **WHEN** a shared live-agent registry record exists without a matching authoritative server registration record or a verifiable live tmux target
- **THEN** `houmao-server` does not admit that session into its primary known-session registry from the shared registry alone
- **AND THEN** shared registry remains compatibility evidence rather than the watch authority

## MODIFIED Requirements

### Requirement: `houmao-server` owns persistent background watch workers for live terminals
For known tmux-backed Houmao sessions and their live terminals that require Houmao-owned watch behavior, `houmao-server` SHALL run persistent background watch workers independent of whether a caller is currently waiting on one request.

Those watch workers SHALL continuously:

- reconcile against the server's known-session registry,
- inspect tmux session and pane state directly,
- inspect the pane process tree to determine whether the supported TUI is up or down,
- capture pane text directly from tmux when a supported TUI process is running, and
- derive Houmao-owned live state without routing parsing or state tracking through the child `cao-server`.

When the tmux session remains alive but the supported TUI process is down, the watch worker SHALL remain active and SHALL record that condition in the tracked state rather than terminating.

The server SHALL stop or release a watch worker only when the tmux session disappears, the tracked session is no longer known to the server, or the server shuts down.

#### Scenario: Terminal watch continues while no client request is active
- **WHEN** a known tmux-backed live session remains alive and no caller is currently polling or waiting on a request
- **THEN** the corresponding `houmao-server` watch worker continues observing that session in the background
- **AND THEN** the latest Houmao-owned live state remains fresh without requiring a new prompt submission or state query

#### Scenario: TUI-down state does not stop the watch worker
- **WHEN** a watched tmux session still exists but the supported TUI process inside that tmux container is down
- **THEN** `houmao-server` keeps the watch worker active for that session
- **AND THEN** the tracked state records the TUI-down condition instead of treating the session as no longer watchable

#### Scenario: Watch worker lifecycle follows tmux lifecycle
- **WHEN** a watched tmux session disappears or the tracked session is removed from the server's known-session registry
- **THEN** the server stops or releases the corresponding watch worker
- **AND THEN** it does not leave a detached background watcher running for that no-longer-live session

### Requirement: `houmao-server` classifies persistence into filesystem-authoritative, transitional compatibility, and memory-primary state
`houmao-server` SHALL distinguish between durable filesystem-authoritative artifacts that remain canonical on disk, transitional compatibility artifacts that remain filesystem-backed in v1 but are intended to move behind server-owned query APIs later, and live control-plane state that becomes server-owned memory.

At minimum, the filesystem-authoritative bucket SHALL include:

- runtime home roots and runtime manifests,
- durable session roots and session manifests,
- mailbox storage,
- workspace-local job directories,
- server-managed session registration bridges,
- Houmao-owned server roots,
- logs, and
- child-supervision support files that remain part of the server's managed runtime.

At minimum, the transitional compatibility bucket SHALL include shared registry live-agent records for v1.

At minimum, the memory-primary bucket SHALL include:

- the known-session registry,
- live request and terminal/session registries,
- watch-worker bindings,
- latest parsed TUI state,
- bounded recent transitions or recent-state history,
- current live control-plane views, and
- child-supervisor live bookkeeping.

`houmao-server` SHALL NOT require per-terminal watch snapshot files or append-only watch logs as part of the authoritative live TUI tracking contract.

#### Scenario: Live TUI tracking state exists only in memory
- **WHEN** `houmao-server` updates live parsed TUI state for a watched session
- **THEN** the authoritative truth for that live tracking state exists in server memory
- **AND THEN** the server does not need a persisted watch snapshot file or append-only watch log to treat that state as authoritative

#### Scenario: Shared registry remains on disk without becoming live TUI truth
- **WHEN** `houmao-server` keeps using shared registry records as a v1 compatibility bridge
- **THEN** those registry files may remain on disk
- **AND THEN** they do not become the authoritative source of live tracked TUI state

#### Scenario: Child adapter files stay hidden under Houmao-owned storage
- **WHEN** `houmao-server` supervises a child `cao-server`
- **THEN** any child-required filesystem state lives under Houmao-owned server storage rather than a separate public CAO-home surface
- **AND THEN** child launcher pid, ownership, or support files remain internal implementation detail or server compatibility views rather than the public control plane

### Requirement: `houmao-server` publishes Houmao-owned terminal state and history as explicit extension routes
`houmao-server` SHALL expose Houmao-specific HTTP extension routes for live terminal state and bounded recent transition history in addition to the CAO-compatible core API.

In v1, those live-state and recent-history routes SHALL remain terminal-keyed compatibility routes, and `houmao-server` SHALL resolve `terminal_id` lookups through a compatibility alias map to its Houmao-owned internal tracked-session identity.

Those extension routes SHALL keep Houmao-owned features explicit rather than using breaking changes on CAO-compatible payloads.

At minimum, the Houmao-owned live terminal state contract SHALL distinguish:

- tmux transport state,
- TUI process state,
- parse status,
- optional probe or parse error detail,
- the latest parsed TUI surface when available,
- operator-facing live state, and
- stability metadata, and
- bounded recent transition or recent-state history when requested.

Those extension routes SHALL be backed by in-memory live state rather than persisted watch files. If recent history is exposed, it SHALL be a bounded in-memory view rather than an append-only persisted log.

#### Scenario: Terminal-keyed route resolves through a compatibility alias
- **WHEN** a caller requests Houmao-owned live state by `terminal_id`
- **THEN** `houmao-server` resolves that lookup through the terminal compatibility alias bound to its internal tracked-session identity
- **AND THEN** the internal known-session registry does not need to be keyed primarily by `terminal_id`

#### Scenario: Callers can inspect Houmao-owned terminal state without scraping raw output
- **WHEN** a caller needs the latest Houmao-owned live state for a watched terminal
- **THEN** the caller can query a dedicated `houmao-server` extension route for that state
- **AND THEN** the caller does not need to reconstruct that state by scraping raw terminal output alone

#### Scenario: Parser or probe failure stays explicit on the extension route
- **WHEN** a watched terminal reaches the extension route with a probe failure or parse failure in the latest cycle
- **THEN** the returned live state distinguishes that failure from a normal TUI-down or successfully parsed cycle
- **AND THEN** the route does not fabricate a parsed surface for that failed cycle

#### Scenario: Recent transitions are exposed from memory rather than persisted watch logs
- **WHEN** a watched terminal has experienced multiple recent observed state changes during the current server lifetime
- **THEN** `houmao-server` may expose those recent transitions through its extension routes
- **AND THEN** that recent-history view is served from bounded in-memory state rather than from append-only persisted watch logs

#### Scenario: Restart rebuilds live state instead of replaying stale watch files
- **WHEN** `houmao-server` restarts and resumes watching still-live known sessions
- **THEN** it rebuilds the extension-route live state from fresh observation of those sessions
- **AND THEN** it does not treat old watch snapshot files or old append-only watch logs as the authoritative rebuilt state
