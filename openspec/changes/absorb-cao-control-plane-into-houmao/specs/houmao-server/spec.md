## ADDED Requirements

### Requirement: `houmao-server` serves `/cao/*` through a Houmao-owned control core
`houmao-server` SHALL satisfy the supported `/cao/*` compatibility surface through the Houmao-owned CAO-compatible control core rather than by proxying to a separate child `cao-server`.

`houmao-server` current-instance, health, and install behavior MAY expose Houmao-owned control-core status, but they SHALL NOT require or publish child-CAO process identity as part of the supported public contract.

#### Scenario: Compatibility routes resolve locally inside `houmao-server`
- **WHEN** a caller uses a supported `/cao/*` route against `houmao-server`
- **THEN** the server dispatches that route into its local control core
- **AND THEN** the caller does not need a hidden child listener for the route to succeed

#### Scenario: Root health omits child-CAO process metadata after absorption
- **WHEN** a caller queries `GET /health` or `GET /houmao/server/current-instance` on a running `houmao-server`
- **THEN** those routes report Houmao-owned server state and any Houmao-owned control-core status that the server chooses to expose
- **AND THEN** they do not require a `child_cao` process record to describe the supported server state

## MODIFIED Requirements

### Requirement: `houmao-server` separates direct watch observation from CAO-compatible control delegation
`houmao-server` SHALL keep its live watch and parsing path separate from its CAO-compatible control authority.

For live TUI parsing and continuous state tracking, `houmao-server` SHALL observe tmux and process state directly.

For CAO-compatible create, mutate, or control routes, `houmao-server` SHALL use its Houmao-owned control core through the explicit upstream-adapter boundary.

Those control operations SHALL NOT become the authoritative parser or live-state source for watched sessions.

#### Scenario: Local control authority does not replace watch authority
- **WHEN** `houmao-server` creates a session, delivers input, or exits a terminal through the Houmao-owned control core
- **THEN** that control action does not make the control core the authoritative parser or live-state reducer for the watched session
- **AND THEN** the watch plane continues to use direct tmux and process observation

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
- Houmao-managed compatibility profile-store artifacts.

At minimum, the transitional compatibility bucket SHALL include shared registry live-agent records for v1 and any persisted compatibility-only inbox queue artifacts if the implementation chooses to store them.

At minimum, the memory-primary bucket SHALL include:

- the known-session registry,
- live request and terminal/session registries,
- watch-worker bindings,
- latest parsed TUI state,
- bounded recent transitions or recent-state history,
- current live control-plane views, and
- control-core live bookkeeping.

`houmao-server` SHALL NOT require per-terminal watch snapshot files or append-only watch logs as part of the authoritative live TUI tracking contract.

#### Scenario: Live TUI tracking state exists only in memory
- **WHEN** `houmao-server` updates live parsed TUI state for a watched session
- **THEN** the authoritative truth for that live tracking state exists in server memory
- **AND THEN** the server does not need a persisted watch snapshot file or append-only watch log to treat that state as authoritative

#### Scenario: Shared registry remains on disk without becoming live TUI truth
- **WHEN** `houmao-server` keeps using shared registry records as a v1 compatibility bridge
- **THEN** those registry files may remain on disk
- **AND THEN** they do not become the authoritative source of live tracked TUI state

#### Scenario: Compatibility profile state stays behind Houmao-owned storage
- **WHEN** `houmao-server` needs stored compatibility profiles to create or bootstrap a terminal
- **THEN** it reads those profiles from Houmao-owned server storage
- **AND THEN** callers do not manage a separate CAO-home contract as part of the supported public surface

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

In v1 after this change, the system SHALL provide a Houmao-owned native CAO-compatible engine behind that boundary, composed from a tmux controller, provider adapters, a profile store, and CAO compatibility projection layers.

The public `houmao-server` API SHALL remain Houmao-owned even when the implementation continues to compare itself to CAO as a parity oracle.

#### Scenario: V1 server serves terminal lifecycle from the native control core
- **WHEN** a caller creates a terminal through `houmao-server` in the supported pair
- **THEN** `houmao-server` may use its Houmao-owned CAO-compatible engine to create the underlying terminal
- **AND THEN** the caller still interacts with `houmao-server` as the public session authority

#### Scenario: Compatibility-core degradation does not make root health unreadable
- **WHEN** the native compatibility control core becomes degraded while `houmao-server` is still running
- **THEN** `GET /health` on `houmao-server` still reports server-local liveness
- **AND THEN** Houmao-owned terminal state reflects upstream or provider degradation separately from server process health

### Requirement: `houmao-server` compatibility SHALL be verified against a real `cao-server`
The implementation SHALL include verification that uses the pinned `cao-server` source to exercise the CAO-compatible HTTP routes exposed under `/cao/*` and the Houmao-owned server behavior that sits around those routes.

Because `houmao-server` no longer proxies those routes to a child CAO process in the supported runtime path, verification SHALL focus on behavioral parity between the Houmao-owned implementation and the pinned CAO oracle rather than on passthrough wiring alone.

That compatibility verification SHALL cover at minimum:

- `/cao/*` endpoint availability and routing
- path-segment encoding and routing
- request argument, query, and request-body handling
- required-versus-optional input handling
- additive-extension safety on `/cao/*` compatibility routes
- compatibility inbox behavior where those routes remain exposed

Houmao-owned behavior SHALL be tested directly and more strictly. That verification SHALL cover at minimum:

- root `/health` pair-health behavior
- current-instance persistence and reporting
- launch registration behavior
- terminal state and history route correctness
- watch-worker lifecycle and runtime-owned state reduction
- install behavior against the Houmao-owned profile store
- migration-failure behavior for deprecated standalone CAO surfaces

#### Scenario: `/cao` parity verification catches request-surface regressions
- **WHEN** a `houmao-server` compatibility route under `/cao/*` changes in a way that breaks CAO-compatible path, query, or body handling
- **THEN** parity verification against the pinned `cao-server` detects the divergence
- **AND THEN** the implementation can reject that change before claiming compatibility-safe behavior

#### Scenario: Houmao-owned verification catches root or native-route regressions
- **WHEN** a Houmao-owned root route or `/houmao/*` route changes in a way that breaks server-owned behavior
- **THEN** direct Houmao behavior verification detects the regression
- **AND THEN** the implementation can reject that change even though `/cao/*` parity may still succeed

### Requirement: `houmao-server` exposes a pair-owned install surface for child-managed profile state
`houmao-server` SHALL expose a Houmao-owned install surface that lets paired clients install compatibility profiles into the server-managed Houmao profile store without direct access to internal storage layout details.

That install surface SHALL accept the install inputs needed by the supported pair, including the provider plus agent source or profile reference needed for the install operation.

`houmao-server` SHALL resolve compatibility profile-store paths internally. The public contract SHALL NOT require callers to provide or compute CAO-home-like paths or hidden control-core storage locations.

#### Scenario: Pair client installs profile through the public server authority
- **WHEN** a paired client submits a profile-install request to `houmao-server` for provider `codex`
- **THEN** `houmao-server` performs that install against its Houmao-managed compatibility profile store
- **AND THEN** the caller does not need to inspect or mutate hidden profile-store filesystem layout directly

#### Scenario: Failed pair-owned install returns an explicit server-owned error
- **WHEN** the underlying install operation fails while `houmao-server` is handling a pair-owned install request
- **THEN** `houmao-server` returns an explicit failure through the public Houmao surface
- **AND THEN** the caller does not need to infer failure indirectly from missing files under internal compatibility storage

## REMOVED Requirements

### Requirement: `houmao-server` supervises a child `cao-server` in the shallow cut
**Reason**: The supported pair now absorbs the used CAO control-plane slice into a Houmao-owned native control core, so child-CAO runtime supervision is no longer part of the supported server contract.
**Migration**: Use `houmao-server` `/cao/*` routes and pair-owned install/status surfaces as before, but do not depend on a hidden child listener, derived child port, or child-managed CAO home layout.

### Requirement: `houmao-server` no-child mode keeps Houmao root health independent from child-CAO readiness
**Reason**: After child-CAO removal there is no separate child readiness mode to expose or suppress.
**Migration**: Treat root `GET /health` and `GET /houmao/server/current-instance` as Houmao-owned server state only, and use `/cao/*` route behavior plus Houmao-owned control-core status fields for compatibility-surface readiness.
