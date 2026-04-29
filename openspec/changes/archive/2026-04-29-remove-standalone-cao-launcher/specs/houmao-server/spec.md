## MODIFIED Requirements

### Requirement: `houmao-server` serves `/cao/*` through a Houmao-owned control core
`houmao-server` SHALL satisfy the supported `/cao/*` compatibility surface through the Houmao-owned CAO-compatible control core rather than by proxying to a separate child `cao-server`.

`houmao-server` current-instance and health behavior MAY expose Houmao-owned control-core status, but they SHALL NOT require or publish child-CAO process identity as part of the supported public contract.

`houmao-server` startup and configuration surfaces SHALL NOT expose child-CAO process controls, including `startup_child`, `child_startup_timeout_seconds`, `--startup-child`, `--no-startup-child`, derived child listener URLs, child launcher config paths, or child ownership roots.

In v1, `houmao-server` MAY preserve the existing `/cao/*` route-handler boundary through a server-local compatibility transport that projects control-core results back into the current route surface.

#### Scenario: Compatibility routes resolve locally inside `houmao-server`
- **WHEN** a caller uses a supported `/cao/*` route against `houmao-server`
- **THEN** the server dispatches that route into its local control core
- **AND THEN** the caller does not need a hidden child listener for the route to succeed

#### Scenario: Root health omits child-CAO process metadata after absorption
- **WHEN** a caller queries `GET /health` or `GET /houmao/server/current-instance` on a running `houmao-server`
- **THEN** those routes report Houmao-owned server state and any Houmao-owned control-core status that the server chooses to expose
- **AND THEN** they do not include a `child_cao` process record to describe the supported server state

#### Scenario: Root health keeps pair compatibility identity fields
- **WHEN** a pair-owned client queries `GET /health` on a running `houmao-server`
- **THEN** the response still includes `service="cli-agent-orchestrator"` and `houmao_service="houmao-server"`
- **AND THEN** child-CAO-specific metadata is absent

#### Scenario: Server startup help omits child-CAO flags
- **WHEN** an operator inspects `houmao-server serve --help` or `houmao-mgr server start --help`
- **THEN** the command help does not list child-CAO startup flags
- **AND THEN** detached server startup does not replay child-CAO startup arguments
