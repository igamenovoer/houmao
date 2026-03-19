## ADDED Requirements

### Requirement: `houmao-server` maps the targeted CAO HTTP endpoint surface
The system SHALL provide a first-party HTTP service named `houmao-server`.

`houmao-server` SHALL expose an HTTP API shaped closely enough to `cao-server` that current Houmao-side session and terminal control flows can migrate with minimal changes.

For the targeted CAO version supported by this change, `houmao-server` SHALL map the CAO HTTP endpoint surface through corresponding `houmao-server` routes, preserving methods, paths, request parameter names, and response shapes closely enough to support drop-in replacement.

At minimum, the mapped compatibility routes SHALL include:

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

#### Scenario: Compatibility routes cover the current CAO session and terminal surface
- **WHEN** a caller uses the targeted CAO session, terminal, input, output, interrupt, deletion, or inbox routes against `houmao-server`
- **THEN** `houmao-server` accepts the same route family with CAO-compatible request semantics
- **AND THEN** the caller does not need a separate route rewrite layer just to switch from `cao-server` to `houmao-server`

#### Scenario: Health endpoint works as the basic liveness probe
- **WHEN** a caller queries `GET /health` on a running `houmao-server`
- **THEN** the server returns a structured health payload indicating the server is alive
- **AND THEN** callers can use that route as the basic liveness check before trusting the server

### Requirement: `houmao-server` supervises a child `cao-server` in the shallow cut
In v1, `houmao-server` SHALL start and supervise a child `cao-server` subprocess as part of its own managed runtime.

For most mapped CAO-compatible HTTP routes in the shallow cut, `houmao-server` SHALL dispatch the corresponding work to that child `cao-server` rather than re-implementing CAO logic natively.

The child `cao-server` SHALL listen on a loopback endpoint whose port is derived mechanically as `houmao-server` port `+1`.

User-facing interfaces for `houmao-server` SHALL NOT expose a separate option to configure that internal child CAO port.

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

#### Scenario: Direct child CAO access is not a supported operator contract
- **WHEN** an external caller reaches the child `cao-server` directly by manually targeting the derived internal port
- **THEN** that access is treated as unsupported debug or user-hack behavior
- **AND THEN** the supported public compatibility surface remains `houmao-server`

### Requirement: `houmao-server` owns persistent background watch workers for live terminals
For live terminals that require Houmao-owned watch behavior, `houmao-server` SHALL run persistent background watch workers independent of whether a caller is currently waiting on one request.

Those watch workers SHALL continuously observe the live terminal surface, derive Houmao-owned state, and persist watch outputs without requiring demo-only monitor processes or request-scoped polling loops.

The server SHALL stop or detach those watch workers in a way consistent with terminal teardown or server shutdown.

#### Scenario: Terminal watch continues while no client request is active
- **WHEN** a live terminal remains idle and no caller is currently polling or waiting on a request
- **THEN** the terminal's `houmao-server` watch worker continues observing the terminal surface
- **AND THEN** the latest Houmao-owned terminal state remains fresh without requiring a new prompt submission

#### Scenario: Watch worker lifecycle follows terminal lifecycle
- **WHEN** a live terminal is deleted through `houmao-server`
- **THEN** the server stops or releases the corresponding watch worker
- **AND THEN** it does not leave a detached background watcher running for that deleted terminal

### Requirement: `houmao-server` publishes Houmao-owned terminal state and history as explicit extension routes
`houmao-server` SHALL expose Houmao-specific HTTP extension routes for terminal watch state and history in addition to the CAO-like core API.

Those extension routes SHALL keep Houmao-owned features explicit rather than silently overloading CAO-compatible payloads.

At minimum, the Houmao-owned terminal state contract SHALL distinguish:

- the latest raw observed terminal surface
- server-owned queued or active work state
- last external-activity marker
- operator-facing terminal state

The server SHALL persist append-only sample and transition history for watched terminals so operators and tooling can inspect recent state evolution.

#### Scenario: Callers can inspect Houmao-owned terminal state without scraping raw output
- **WHEN** a caller needs the latest Houmao-owned watch state for a live terminal
- **THEN** the caller can query a dedicated `houmao-server` extension route for that state
- **AND THEN** the caller does not need to reconstruct that state by scraping raw terminal output alone

#### Scenario: Sample and transition history remain available for debugging
- **WHEN** a watched terminal has experienced multiple observed state changes
- **THEN** `houmao-server` retains append-only sample and transition history for that terminal
- **AND THEN** operators can inspect that history through server-owned artifacts or extension routes

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
