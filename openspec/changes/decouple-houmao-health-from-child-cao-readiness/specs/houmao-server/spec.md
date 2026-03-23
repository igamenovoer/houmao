## ADDED Requirements

### Requirement: `houmao-server` no-child mode keeps Houmao root health independent from child-CAO readiness
When `houmao-server` starts with child startup disabled, its Houmao-owned health and current-instance routes SHALL remain available for server-local readiness checks without requiring a running child `cao-server`.

In that mode, `GET /health` and `GET /houmao/server/current-instance` SHALL represent the Houmao-owned server state only, and `child_cao` SHALL be absent rather than projected as an unhealthy derived-port probe.

CAO-dependent readiness SHALL remain a compatibility-surface concern and SHALL be checked through `/cao/*` behavior rather than inferred from Houmao root health.

#### Scenario: Root health stays ready when child startup is disabled
- **WHEN** `houmao-server` starts with `startup_child=false`
- **THEN** `GET /health` reports Houmao-server liveness without requiring child-CAO health
- **AND THEN** the response omits `child_cao`

#### Scenario: Current-instance omits child metadata when no child is started
- **WHEN** `houmao-server` starts with `startup_child=false`
- **THEN** `GET /houmao/server/current-instance` reports the live Houmao-server identity and runtime root
- **AND THEN** the response omits `child_cao`

#### Scenario: Native managed-headless routes do not inherit CAO readiness requirements
- **WHEN** a caller uses Houmao-owned managed-headless routes on a `houmao-server` started with `startup_child=false`
- **THEN** the server may admit that native managed-headless work without a running child `cao-server`
- **AND THEN** the caller does not need child-CAO health to treat the Houmao-owned server as ready
