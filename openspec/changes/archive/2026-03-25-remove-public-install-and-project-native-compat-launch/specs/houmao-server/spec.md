## MODIFIED Requirements

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
- session-backed native-selector resolution and launch-time compatibility projection
- migration-failure behavior for deprecated standalone CAO surfaces

#### Scenario: `/cao` parity verification catches request-surface regressions
- **WHEN** a `houmao-server` compatibility route under `/cao/*` changes in a way that breaks CAO-compatible path, query, or body handling
- **THEN** parity verification against the pinned `cao-server` detects the divergence
- **AND THEN** the implementation can reject that change before claiming compatibility-safe behavior

#### Scenario: Houmao-owned verification catches root or native-route regressions
- **WHEN** a Houmao-owned root route or `/houmao/*` route changes in a way that breaks server-owned behavior
- **THEN** direct Houmao behavior verification detects the regression
- **AND THEN** the implementation can reject that change even though `/cao/*` parity may still succeed

## REMOVED Requirements

### Requirement: `houmao-server` exposes a pair-owned install surface for compatibility profile state
**Reason**: Public compatibility-profile install is no longer part of the supported pair workflow once session-backed launch resolves native agent definitions directly and synthesizes any needed compatibility artifacts at launch time.

**Migration**: Launch through the supported pair using native agent-definition inputs; do not preload compatibility profiles through a public server install route.
