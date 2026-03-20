## ADDED Requirements

### Requirement: `houmao-server` keeps root and `/houmao/*` namespaces Houmao-owned
`houmao-server` SHALL reserve the server root and the `/houmao/*` route family for Houmao-owned pair behavior.

CAO compatibility SHALL live only under the explicit `/cao/*` route family.

`houmao-server` SHALL NOT expose root-level CAO-compatible session or terminal routes such as `/sessions/*` or `/terminals/*` as part of the supported public contract.

The root `GET /health` route SHALL remain a Houmao-owned pair-health route rather than a CAO-compatible route. CAO-compatible health SHALL be exposed through `/cao/health`.

#### Scenario: Root CAO session route is not part of the supported public contract
- **WHEN** a caller looks for the CAO-compatible session list surface on `houmao-server`
- **THEN** the supported compatibility route is `GET /cao/sessions`
- **AND THEN** `houmao-server` does not expose `GET /sessions` as a supported CAO-compatible route

#### Scenario: Root health remains Houmao-owned while CAO health is namespaced
- **WHEN** a caller needs Houmao pair health from `houmao-server`
- **THEN** the caller uses `GET /health`
- **AND THEN** a caller that needs the CAO-compatible health route uses `GET /cao/health`

## MODIFIED Requirements

### Requirement: `houmao-server` matches the full supported `cao-server` HTTP API
The system SHALL provide a first-party HTTP service named `houmao-server`.

`houmao-server` SHALL expose an HTTP API that is fully compatible with the public HTTP API of the supported `cao-server` version under an explicit `/cao` compatibility namespace.

For the supported `cao-server` version pinned by this change, every public `cao-server` HTTP endpoint SHALL have a corresponding `houmao-server` behavior under `/cao` that preserves the CAO route shape beneath that prefix, methods, request argument names, request-body semantics, response status codes, and response bodies closely enough that work that succeeds against `cao-server` also succeeds against `houmao-server` through `/cao`.

The following routes are explicitly called out because current Houmao usage already depends on them, but compatibility SHALL NOT be limited to this subset:

- `GET /cao/health`
- `GET /cao/sessions`
- `POST /cao/sessions`
- `DELETE /cao/sessions/{session_name}`
- `GET /cao/sessions/{session_name}/terminals`
- `POST /cao/sessions/{session_name}/terminals`
- `GET /cao/terminals/{terminal_id}`
- `POST /cao/terminals/{terminal_id}/input`
- `GET /cao/terminals/{terminal_id}/output`
- `POST /cao/terminals/{terminal_id}/exit`
- `DELETE /cao/terminals/{terminal_id}`
- `POST /cao/terminals/{terminal_id}/inbox/messages`
- `GET /cao/terminals/{terminal_id}/inbox/messages`

#### Scenario: Any supported `cao-server` endpoint continues to work through `/cao`
- **WHEN** a caller uses any public HTTP endpoint supported by the pinned `cao-server` version against `houmao-server` through the `/cao` namespace
- **THEN** `houmao-server` accepts the same call pattern with CAO-compatible semantics
- **AND THEN** work that succeeds against `cao-server` also succeeds against `houmao-server` without requiring root-route compatibility aliases

#### Scenario: Namespaced CAO health remains available for compatibility callers
- **WHEN** a caller queries `GET /cao/health` on a running `houmao-server`
- **THEN** the server returns a CAO-compatible health payload for the compatibility surface
- **AND THEN** the caller does not need the root `GET /health` route to preserve CAO semantics

### Requirement: Houmao extensions on CAO-compatible routes are additive only
When `houmao-server` extends an existing CAO-compatible route under `/cao/*`, those extensions SHALL be additive only.

Additive extensions MAY include:

- additional optional request arguments or body fields
- additional optional response fields
- additional new endpoints outside the CAO-compatible route set

`houmao-server` SHALL NOT require Houmao-only arguments or fields in order for a CAO-compatible request under `/cao/*` to succeed, and it SHALL NOT remove or repurpose CAO-defined fields or behaviors on those compatibility routes.

This additive-only restriction SHALL apply to the `/cao/*` compatibility surface. It SHALL NOT require Houmao-owned root routes or `/houmao/*` routes to preserve CAO route shape or CAO naming.

#### Scenario: CAO-compatible callers ignore additive fields on `/cao` safely
- **WHEN** `houmao-server` returns a CAO-compatible response body from a `/cao/*` route with additional Houmao-owned optional fields
- **THEN** a CAO-compatible client that only reads CAO-defined fields still succeeds
- **AND THEN** the additive fields do not break the compatibility contract

#### Scenario: Houmao-owned root routes are not constrained to CAO route shape
- **WHEN** `houmao-server` exposes a Houmao-owned root route or `/houmao/*` route
- **THEN** that route may use Houmao-defined semantics without preserving CAO route names or payload shape
- **AND THEN** the additive-only CAO rule remains scoped to `/cao/*`

### Requirement: Pair-owned `houmao-server` clients keep persisted authority at the server root
When pair-owned Houmao code persists or exchanges `houmao-server` connection state for runtime resume, gateway attach, demos, or query helpers, that persisted authority SHALL remain the public `houmao-server` root base URL rather than a `/cao`-qualified compatibility URL.

The explicit `/cao/*` namespace SHALL be applied through one shared pair-owned compatibility client seam rather than by storing caller-specific compatibility-prefixed base URLs in manifests, attach metadata, or other pair-owned persisted state.

Pair-owned code that needs CAO-compatible session or terminal behavior against `houmao-server` SHALL consume that shared compatibility client seam instead of reconstructing plain root-path `CaoRestClient` instances from persisted `api_base_url` values.

#### Scenario: Runtime resume keeps persisted server authority rooted at the public base URL
- **WHEN** Houmao runtime state persists `houmao-server` connection metadata for a resumable `houmao_server_rest` session
- **THEN** the persisted `api_base_url` remains the public `houmao-server` root authority
- **AND THEN** resumed CAO-compatible session control derives `/cao/*` behavior through the shared compatibility client seam rather than by persisting a `/cao`-qualified URL

#### Scenario: Gateway attach and demos share the same `/cao` client seam
- **WHEN** gateway attach code or a repo-owned demo reconstructs a pair-owned client from persisted or configured `houmao-server` state
- **THEN** that caller uses the same shared compatibility client seam for CAO-compatible session or terminal routes
- **AND THEN** the caller does not invent its own root-path or persisted `/cao` rewrite logic

### Requirement: `houmao-server` supervises a child `cao-server` in the shallow cut
In v1, `houmao-server` SHALL start and supervise a child `cao-server` subprocess as part of its own managed runtime.

For most mapped CAO-compatible HTTP routes under `/cao/*` in the shallow cut, `houmao-server` SHALL dispatch the corresponding work to that child `cao-server` rather than re-implementing CAO logic natively.

The child `cao-server` SHALL listen on a loopback endpoint whose port is derived mechanically as `houmao-server` port `+1`.

User-facing interfaces for `houmao-server` SHALL NOT expose a separate option to configure that internal child CAO port.

When the child `cao-server` requires `HOME` or other on-disk support state, `houmao-server` SHALL provision and manage that state under Houmao-owned server storage rather than exposing a separate user-facing CAO-home contract.

The detailed layout and contents of that internal child-CAO storage SHALL be treated as opaque implementation detail rather than as a supported public filesystem surface.

Direct use of the child CAO endpoint by an external caller who already knows that derived port SHALL be treated as an unsupported debug or user hack rather than as a supported public interface.

`houmao-server` SHALL keep its own health and lifecycle distinct from the child `cao-server` health so callers can distinguish "Houmao server is alive" from "child CAO is healthy."

#### Scenario: Shallow-cut compatibility routing dispatches `/cao` work to the child CAO server
- **WHEN** a caller creates or mutates a CAO-compatible session or terminal through a `/cao/*` route on `houmao-server`
- **THEN** `houmao-server` may dispatch that route to its supervised child `cao-server`
- **AND THEN** the caller still interacts with the public `houmao-server` compatibility surface rather than the hidden child listener

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
- **AND THEN** the supported public compatibility surface remains `houmao-server` through `/cao/*`

### Requirement: Existing CAO-compatible and terminal-keyed routes remain TUI-specific compatibility surfaces
When `houmao-server` adds headless managed-agent support, it SHALL keep existing CAO-compatible `/cao/sessions/*` and `/cao/terminals/*` routes plus existing `/houmao/terminals/{terminal_id}/*` routes as TUI-specific or CAO-compatible surfaces.

`houmao-server` SHALL NOT publish registered headless managed agents as fake CAO sessions or fake terminals on those routes.

Headless managed agents SHALL instead be exposed through the Houmao-owned `/houmao/agents/*` route family.

#### Scenario: Headless managed agent stays off terminal-keyed compatibility routes
- **WHEN** `houmao-server` is managing a registered headless Claude agent
- **THEN** that headless agent is available through `/houmao/agents/*`
- **AND THEN** the server does not fabricate a terminal-keyed compatibility entry for it on `/houmao/terminals/{terminal_id}/*`

#### Scenario: TUI compatibility routes remain available for terminal-backed sessions
- **WHEN** `houmao-server` is managing a TUI-backed session that already has a `terminal_id`
- **THEN** callers can continue using `/cao/sessions/*`, `/cao/terminals/*`, and the existing terminal-keyed compatibility routes for that session
- **AND THEN** adding headless managed-agent support does not remove or rename the TUI compatibility surface outside the explicit `/cao` namespace move

### Requirement: `houmao-server` compatibility SHALL be verified against a real `cao-server`
The implementation SHALL include verification that uses the pinned `cao-server` source to exercise the CAO-compatible HTTP routes exposed under `/cao/*` and the Houmao-owned server behavior that sits around those routes.

For passthrough CAO-compatible routes, verification SHALL focus on whether `houmao-server` forwards the request surface correctly so the child `cao-server` accepts or rejects the input in the expected compatibility-significant places.

That passthrough verification SHALL cover at minimum:

- `/cao/*` endpoint availability and routing
- path-segment encoding and routing
- request argument, query, and request-body handling
- required-versus-optional input handling
- additive-extension safety on `/cao/*` compatibility routes

That passthrough verification SHALL NOT need to re-test the downstream session, terminal, or provider behavior once the child `cao-server` has accepted the forwarded input.

Houmao-owned behavior SHALL be tested directly and more strictly. That verification SHALL cover at minimum:

- root `/health` pair-health behavior
- current-instance persistence and reporting
- launch registration behavior
- terminal state and history route correctness
- watch-worker lifecycle and runtime-owned state reduction
- runtime routing behavior owned by Houmao rather than by CAO

#### Scenario: `/cao` passthrough verification catches request-surface regressions
- **WHEN** a `houmao-server` compatibility route under `/cao/*` changes in a way that breaks CAO-compatible path, query, or body handling
- **THEN** passthrough verification against the pinned `cao-server` detects the divergence
- **AND THEN** the implementation can reject that change before claiming compatibility-safe delegation

#### Scenario: Houmao-owned verification catches root or native-route regressions
- **WHEN** a Houmao-owned root route or `/houmao/*` route changes in a way that breaks server-owned behavior
- **THEN** direct Houmao behavior verification detects the regression
- **AND THEN** the implementation can reject that change even if the delegated child CAO still accepts the underlying compatibility request

### Requirement: Session detail responses preserve terminal summary metadata needed by pair clients
For the CAO-compatible `GET /cao/sessions/{session_name}` route, `houmao-server` SHALL preserve the session-detail structure and terminal-summary metadata exposed by the supported CAO source closely enough that paired Houmao clients can consume that response as a typed contract.

At minimum, the session-detail response SHALL let a pair client identify the created terminal id together with the tmux session and tmux window metadata carried by the supported CAO session summary.

#### Scenario: Session detail exposes terminal window metadata for paired clients
- **WHEN** a caller queries `GET /cao/sessions/{session_name}` through `houmao-server` for a live session whose terminal summary includes tmux window metadata in the supported CAO source
- **THEN** the `houmao-server` response preserves that terminal summary metadata on the compatibility route
- **AND THEN** paired Houmao clients can persist that tmux window identity into registration or runtime artifacts without scraping unrelated routes

#### Scenario: Session detail remains compatible for callers that ignore extra terminal summary fields
- **WHEN** a CAO-compatible caller reads the `GET /cao/sessions/{session_name}` response but ignores terminal summary fields it does not use
- **THEN** the compatibility response still succeeds as a valid session-detail view
- **AND THEN** preserving tmux session or window metadata does not force callers onto a separate Houmao-only route just to use the pair
