## MODIFIED Requirements

### Requirement: CAO REST client matches the vendored CAO API contract
The system SHALL implement a CAO-compatible REST client whose request parameter names, parameter locations, and response shapes match the pinned CAO server API contract.

For the supported pair, that client SHALL target the Houmao-owned compatibility authority exposed by `houmao-server` under `/cao/*` rather than requiring a standalone `cao-server` as the supported endpoint.

Pair-owned persisted authority SHALL remain the public `houmao-server` root base URL. The CAO compatibility prefix SHALL be applied through one shared compatibility client seam rather than by persisting `/cao`-qualified base URLs.

The supported pair MAY continue to reuse that repo-owned CAO-compatible client seam internally during v1, but that internal seam SHALL NOT require a local `cao-server` executable or a caller-managed CAO profile-store path as a precondition for supported pair workflows.

For supported loopback compatibility base URLs (`http://localhost:<port>`,
`http://127.0.0.1:<port>` with explicit ports), the CAO-compatible REST client SHALL bypass ambient proxy environment variables by default by ensuring loopback entries exist in `NO_PROXY` and `no_proxy`.

When `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`, the CAO-compatible REST client SHALL NOT modify `NO_PROXY` or `no_proxy` and will respect caller-provided values.

#### Scenario: Create terminal uses CAO query parameters against the pair compatibility surface
- **WHEN** a pair-owned client requests creation of a compatibility terminal in session `S` for provider `P`, agent profile `A`, and working directory `W`
- **THEN** the CAO-compatible client issues a `POST /cao/sessions/{S}/terminals` request using CAO's parameter names (`provider`, `agent_profile`, `working_directory`)
- **AND THEN** the client does not send incompatible JSON payload keys

#### Scenario: Send terminal input uses the CAO `message` parameter through `houmao-server`
- **WHEN** the pair-owned client sends input text `T` to terminal `TERM_ID`
- **THEN** the CAO-compatible client issues `POST /cao/terminals/{TERM_ID}/input` using CAO's parameter name `message=T`
- **AND THEN** the supported authority for that request is `houmao-server`

#### Scenario: Pair-backed runtime startup keeps the shared CAO client seam without raw CAO startup requirements
- **WHEN** the pair starts a `houmao_server_rest` session through its shared CAO-compatible client seam
- **THEN** that pair workflow may still use repo-owned CAO-compatible client classes internally
- **AND THEN** it does not require `cao-server` on `PATH` or a caller-managed local CAO profile-store path to satisfy the supported pair contract

#### Scenario: Loopback compatibility requests bypass ambient proxy env on a non-default port
- **WHEN** the CAO-compatible client is configured with pair root base URL `http://127.0.0.1:9990`
- **AND WHEN** caller environment includes `HTTP_PROXY`, `HTTPS_PROXY`, or `ALL_PROXY`
- **THEN** client requests to the loopback compatibility authority bypass those proxy endpoints by default

### Requirement: Runtime-generated CAO profiles include required metadata
When using Houmao's CAO-compatible control path, the system SHALL render and store compatibility agent profiles that conform to the pinned CAO agent-profile format and can be loaded by Houmao-owned provider adapters without validation errors.

Those compatibility profiles SHALL live in a Houmao-managed profile store rather than in a caller-managed standalone CAO `HOME`.

#### Scenario: Rendered compatibility profile includes required YAML frontmatter fields
- **WHEN** the system generates a compatibility agent profile for role `R`
- **THEN** the YAML frontmatter includes `name` and `description` as non-empty strings
- **AND THEN** Houmao-owned compatibility profile loading accepts the rendered profile successfully

#### Scenario: Pair install writes compatibility profile into Houmao-managed store
- **WHEN** a pair-owned install flow stores a compatibility profile for provider `codex`
- **THEN** the resulting profile artifact is written into the Houmao-managed profile store
- **AND THEN** callers do not need to manage a separate CAO-home profile directory as part of the supported pair contract
