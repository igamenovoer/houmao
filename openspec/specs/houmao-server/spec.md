## Purpose
Define the public `houmao-server` contract as the Houmao-owned CAO-compatible HTTP authority, its additive extension routes, and its child-CAO shallow-cut lifecycle.

## Requirements

### Requirement: `houmao-server` matches the full supported `cao-server` HTTP API
The system SHALL provide a first-party HTTP service named `houmao-server`.

`houmao-server` SHALL expose an HTTP API that is fully compatible with the public HTTP API of the supported `cao-server` version.

For the supported `cao-server` version pinned by this change, every public `cao-server` HTTP endpoint SHALL have a corresponding `houmao-server` behavior that preserves route paths, methods, request argument names, request-body semantics, response status codes, and response bodies closely enough that work that succeeds against `cao-server` also succeeds against `houmao-server`.

The following routes are explicitly called out because current Houmao usage already depends on them, but compatibility SHALL NOT be limited to this subset:

- `GET /health`
- `GET /sessions`
- `POST /sessions`
- `DELETE /sessions/{session_name}`
- `GET /sessions/{session_name}/terminals`
- `POST /sessions/{session_name}/terminals`
- `GET /terminals/{terminal_id}`
- `POST /terminals/{terminal_id}/input`
- `GET /terminals/{terminal_id}/output`
- `POST /terminals/{terminal_id}/exit`
- `DELETE /terminals/{terminal_id}`
- `POST /terminals/{terminal_id}/inbox/messages`
- `GET /terminals/{terminal_id}/inbox/messages`

#### Scenario: Any supported `cao-server` endpoint continues to work through `houmao-server`
- **WHEN** a caller uses any public HTTP endpoint supported by the pinned `cao-server` version against `houmao-server`
- **THEN** `houmao-server` accepts the same call pattern with CAO-compatible semantics
- **AND THEN** work that succeeds against `cao-server` also succeeds against `houmao-server` without a separate route rewrite layer

#### Scenario: Health endpoint works as the basic liveness probe
- **WHEN** a caller queries `GET /health` on a running `houmao-server`
- **THEN** the server returns a structured health payload indicating the server is alive
- **AND THEN** callers can use that route as the basic liveness check before trusting the server

### Requirement: `houmao-server` compatibility is pinned to one exact CAO source of truth
For this capability, the CAO HTTP compatibility source of truth SHALL be pinned to:

- repository: `https://github.com/imsight-forks/cli-agent-orchestrator.git`
- commit: `0fb3e5196570586593736a21262996ca622f53b6`
- local tracked checkout: `extern/tracked/cli-agent-orchestrator`

The system SHALL treat that exact source as the parity oracle for `houmao-server` API compatibility rather than a floating branch name or whichever `cao-server` happens to be on `PATH`.

#### Scenario: HTTP parity verification uses the pinned CAO source
- **WHEN** implementation or verification compares `houmao-server` behavior to CAO behavior
- **THEN** it uses the pinned CAO source of truth for this capability
- **AND THEN** the parity target does not drift with a floating upstream branch

### Requirement: `houmao-server` compatibility is defined within the supported Houmao pair
The compatibility contract for `houmao-server` SHALL be defined as part of the supported `houmao-server + houmao-srv-ctrl` replacement pair for `cao-server + cao`.

This capability SHALL NOT require `houmao-server` to support arbitrary external `cao` clients as a public compatibility contract.

Mixed-pair usage such as `houmao-server + cao` SHALL be treated as unsupported in this capability.

#### Scenario: Mixed server-plus-raw-CAO usage is not part of the compatibility promise
- **WHEN** an operator points a raw `cao` client at `houmao-server`
- **THEN** that combination is outside the supported compatibility contract for this capability
- **AND THEN** parity verification for the capability does not need to claim that mixed pair works

### Requirement: Houmao extensions on CAO-compatible routes are additive only
When `houmao-server` extends an existing CAO-compatible route, those extensions SHALL be additive only.

Additive extensions MAY include:

- additional optional request arguments or body fields
- additional optional response fields
- additional new endpoints outside the CAO-compatible route set

`houmao-server` SHALL NOT require Houmao-only arguments or fields in order for a CAO-compatible request to succeed, and it SHALL NOT remove or repurpose CAO-defined fields or behaviors on compatibility routes.

#### Scenario: CAO-compatible clients ignore additive response fields safely
- **WHEN** `houmao-server` returns a CAO-compatible response body with additional Houmao-owned optional fields
- **THEN** a CAO-compatible client that only reads CAO-defined fields still succeeds
- **AND THEN** the additive fields do not break the compatibility contract

#### Scenario: Houmao-only request arguments remain optional on compatibility routes
- **WHEN** a caller sends a CAO-compatible request body or argument set without any Houmao-only extension fields
- **THEN** `houmao-server` still processes the request successfully according to CAO-compatible semantics
- **AND THEN** Houmao-only extensions do not become mandatory for compatibility

### Requirement: `houmao-server` supervises a child `cao-server` in the shallow cut
In v1, `houmao-server` SHALL start and supervise a child `cao-server` subprocess as part of its own managed runtime.

For most mapped CAO-compatible HTTP routes in the shallow cut, `houmao-server` SHALL dispatch the corresponding work to that child `cao-server` rather than re-implementing CAO logic natively.

The child `cao-server` SHALL listen on a loopback endpoint whose port is derived mechanically as `houmao-server` port `+1`.

User-facing interfaces for `houmao-server` SHALL NOT expose a separate option to configure that internal child CAO port.

When the child `cao-server` requires `HOME` or other on-disk support state, `houmao-server` SHALL provision and manage that state under Houmao-owned server storage rather than exposing a separate user-facing CAO-home contract.

The detailed layout and contents of that internal child-CAO storage SHALL be treated as opaque implementation detail rather than as a supported public filesystem surface.

Direct use of the child CAO endpoint by an external caller who already knows that derived port SHALL be treated as an unsupported debug or user hack rather than as a supported public interface.

`houmao-server` SHALL keep its own health and lifecycle distinct from the child `cao-server` health so callers can distinguish "Houmao server is alive" from "child CAO is healthy."

#### Scenario: Shallow-cut route handling dispatches to the child CAO server
- **WHEN** a caller creates or mutates a CAO-compatible session or terminal through `houmao-server`
- **THEN** `houmao-server` may dispatch that route to its supervised child `cao-server`
- **AND THEN** the caller still interacts with `houmao-server` as the public compatibility surface

#### Scenario: Child CAO port derives from the public `houmao-server` port
- **WHEN** `houmao-server` starts on loopback port `9890`
- **THEN** the child `cao-server` listens on loopback port `9891`
- **AND THEN** callers cannot configure that internal child port through a separate user-facing option

#### Scenario: Child CAO filesystem state stays behind Houmao-owned storage
- **WHEN** the supervised child `cao-server` needs a home directory or adapter-private support files
- **THEN** `houmao-server` provisions those files under Houmao-owned server storage
- **AND THEN** callers do not manage a separate CAO-home path as part of the public contract

#### Scenario: Direct child CAO access is not a supported operator contract
- **WHEN** an external caller reaches the child `cao-server` directly by manually targeting the derived internal port
- **THEN** that access is treated as unsupported debug or user-hack behavior
- **AND THEN** the supported public compatibility surface remains `houmao-server`

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

### Requirement: `houmao-server` keeps registration bridge storage contained under the server-owned sessions root
When `houmao-server` persists or removes server-owned registration records for tracked sessions, it SHALL treat the registration storage key as a validated server-owned identifier rather than as a raw filesystem path fragment.

`houmao-server` SHALL reject registration or deletion inputs whose session identifier cannot be represented safely inside the configured `sessions/` root.

`houmao-server` SHALL verify that the resolved registration path remains under the configured `sessions/` root before writing or removing any registration directory.

#### Scenario: Invalid registration identifier is rejected before write
- **WHEN** a caller sends a registration request whose session identifier would escape or otherwise violate the server-owned `sessions/` storage namespace
- **THEN** `houmao-server` rejects that request before creating or modifying any registration directory
- **AND THEN** the server does not write a registration file outside the configured `sessions/` root

#### Scenario: Registration cleanup remains root-contained
- **WHEN** `houmao-server` removes a server-owned registration record during session or terminal cleanup
- **THEN** it resolves the cleanup target within the same validated server-owned `sessions/` namespace
- **AND THEN** the server does not remove directories outside the configured `sessions/` root

### Requirement: `houmao-server` keeps background tracking resilient across unexpected runtime failures
`houmao-server` SHALL keep the tracking supervisor and per-session watch workers resilient against unexpected runtime exceptions.

Unexpected reconcile failures SHALL NOT permanently terminate the supervisor thread for the lifetime of the server process.

Unexpected session-poll failures SHALL NOT permanently terminate the corresponding watch worker unless the tracked session has actually left live authority.

When such failures affect live-state observation, `houmao-server` SHALL surface an explicit error state for that session or otherwise record the failure for operator diagnosis rather than silently ceasing background tracking.

#### Scenario: Reconcile failure does not permanently stop the supervisor
- **WHEN** one reconcile pass raises an unexpected runtime exception while loading or reconciling live known sessions
- **THEN** `houmao-server` records or logs that failure and keeps the supervisor available for later reconcile passes
- **AND THEN** continuous background tracking can resume without restarting the server process

#### Scenario: Session poll failure does not permanently stop the worker
- **WHEN** one watch-worker cycle raises an unexpected runtime exception while polling a still-live tracked session
- **THEN** `houmao-server` records an explicit failure for that session and keeps the worker eligible to poll again on a later cycle
- **AND THEN** one bad poll does not permanently disable live tracking for that session

### Requirement: `houmao-server` removes live-state aliases when a tracked session leaves live authority
The terminal-keyed Houmao live-state routes SHALL resolve only through terminal aliases that remain bound to a currently live known session.

When a tracked session leaves the live known-session registry, loses tmux liveness, or is otherwise released from background watch authority, `houmao-server` SHALL evict the corresponding in-memory worker binding, tracker state, and terminal alias from its live authority maps.

#### Scenario: Tmux loss removes stale live-state authority
- **WHEN** a watched tracked session loses tmux liveness and a later reconcile pass no longer admits that session into the live known-session registry
- **THEN** `houmao-server` removes the corresponding in-memory tracker and terminal alias from live authority
- **AND THEN** terminal-keyed live-state lookup no longer succeeds only from stale in-memory residue

#### Scenario: Registry removal releases the live terminal alias
- **WHEN** a tracked session is removed from the authoritative known-session registry even if an older in-memory tracker still exists
- **THEN** `houmao-server` evicts the existing terminal alias and tracker from the live route authority
- **AND THEN** the live-state routes reflect that the session is no longer known to the server

### Requirement: `houmao-server` preserves tracked pane identity during registration-seeded admission
When `houmao-server` admits a tracked session from its registration bridge, it SHALL preserve available tmux pane-targeting metadata needed to select the intended tracked pane on the first live polling cycles.

That registration-seeded identity SHALL include tmux window metadata when the caller provides it, and `houmao-server` SHALL enrich the identity from manifest-backed metadata during admission when a manifest path is available and the registration payload omits that metadata.

The initial tracker state SHALL use that preserved or enriched pane identity rather than falling back blindly to whichever tmux pane is active for the session.

#### Scenario: Registration-supplied window metadata is used immediately
- **WHEN** a registration request includes tmux window identity for the tracked session
- **THEN** `houmao-server` persists and applies that window identity when creating the initial tracked-session record
- **AND THEN** the first live polling cycles target that registered window instead of choosing an arbitrary active pane

#### Scenario: Manifest-backed window metadata enriches the initial tracker
- **WHEN** a registration request omits tmux window identity but supplies a manifest path whose metadata identifies the tracked tmux window
- **THEN** `houmao-server` enriches the initial tracked-session record from that manifest before the first live polling cycles
- **AND THEN** registration-seeded tracking does not need to wait for a later reconcile pass to recover the correct pane target

### Requirement: `houmao-server` uses replaceable upstream adapters and v1 SHALL support a CAO-backed engine
`houmao-server` SHALL interact with underlying live terminal providers through an explicit upstream-adapter boundary rather than embedding one backend's control logic into the public server contract.

That upstream-adapter boundary SHALL support at minimum:

- session creation and deletion
- terminal creation and deletion
- terminal metadata lookup
- terminal output retrieval
- prompt or control input delivery
- interrupt or exit delivery
- upstream health or connectivity checks

In v1, the system SHALL provide an upstream engine that uses the supervised child `cao-server` behind `houmao-server`.

The public `houmao-server` API SHALL remain Houmao-owned even when the v1 implementation delegates core operations to CAO behind that adapter.

#### Scenario: V1 server delegates terminal lifecycle to CAO behind the adapter boundary
- **WHEN** a caller creates a terminal through `houmao-server` in the shallow v1 implementation
- **THEN** `houmao-server` may use the CAO-backed upstream engine to create the underlying terminal
- **AND THEN** the caller still interacts with `houmao-server` as the public session authority

#### Scenario: Upstream CAO loss does not make server-local health unreadable
- **WHEN** the child `cao-server` becomes unavailable while `houmao-server` is still running
- **THEN** `GET /health` on `houmao-server` still reports server-local liveness
- **AND THEN** Houmao-owned terminal state reflects upstream unavailability separately from server process health

### Requirement: `houmao-server` is designed to outgrow CAO rather than permanently mirror it
The system SHALL treat CAO compatibility as a migration strategy, not as the final architecture of `houmao-server`.

The Houmao-owned watch state, persistence, and extension routes SHALL NOT depend on CAO-specific protocol details beyond what the current upstream adapter needs internally.

Future native Houmao-owned terminal backends SHALL be able to replace the CAO-backed adapter without requiring a second public rename away from `houmao-server`.

#### Scenario: Replacing the upstream adapter does not require changing the public server name
- **WHEN** a future implementation replaces the CAO-backed adapter with a native Houmao-owned backend
- **THEN** the public server remains `houmao-server`
- **AND THEN** callers do not need to switch back to CAO-branded service identities to keep using the server

### Requirement: `houmao-server` compatibility SHALL be verified against a real `cao-server`
The implementation SHALL include verification that uses the pinned `cao-server` source to exercise the CAO-compatible HTTP routes that remain passthrough in v1 and the Houmao-owned server behavior that sits around those routes.

For passthrough CAO-compatible routes, verification SHALL focus on whether `houmao-server` forwards the request surface correctly so the child `cao-server` accepts or rejects the input in the expected compatibility-significant places.

That passthrough verification SHALL cover at minimum:

- endpoint availability and routing
- path-segment encoding and routing
- request argument, query, and request-body handling
- required-versus-optional input handling
- additive-extension safety on CAO-compatible routes

That passthrough verification SHALL NOT need to re-test the downstream session, terminal, or provider behavior once the child `cao-server` has accepted the forwarded input.

Houmao-owned behavior SHALL be tested directly and more strictly. That verification SHALL cover at minimum:

- additive `/health` fields and child-lifecycle metadata
- current-instance persistence and reporting
- launch registration behavior
- terminal state and history route correctness
- watch-worker lifecycle and runtime-owned state reduction
- runtime routing behavior owned by Houmao rather than by CAO

#### Scenario: Passthrough verification catches request-surface regressions
- **WHEN** a `houmao-server` passthrough compatibility route changes in a way that breaks CAO-compatible path, query, or body handling
- **THEN** passthrough verification against the pinned `cao-server` detects the divergence
- **AND THEN** the implementation can reject that change before claiming compatibility-safe delegation

#### Scenario: Houmao-owned verification catches extension regressions
- **WHEN** a Houmao-owned extension route or lifecycle reduction changes in a way that breaks server-owned behavior
- **THEN** direct Houmao behavior verification detects the regression
- **AND THEN** the implementation can reject that change even if the delegated child CAO still accepts the underlying request
