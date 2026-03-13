## MODIFIED Requirements

### Requirement: Optional CAO backend via REST boundary
The system SHALL optionally support launching and driving sessions via CAO
using CAO's REST API, without requiring the core runtime to depend on CAO
internals.

For supported loopback CAO base URLs (`http://localhost:<port>`,
`http://127.0.0.1:<port>` with explicit ports), runtime-owned CAO HTTP
communication SHALL bypass ambient proxy environment variables by default by
ensuring loopback entries exist in `NO_PROXY`/`no_proxy`.

When `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`, the runtime SHALL NOT modify `NO_PROXY`
or `no_proxy` and will respect caller-provided values (for example, to enable
traffic-watching development proxies).

#### Scenario: CAO-backed session launch and messaging
- **WHEN** a developer starts a CAO-backed session and provides a CAO API base URL at session start
- **THEN** the system creates a CAO session/terminal, sends prompts, and fetches replies using CAO REST endpoints
- **AND THEN** the system persists the CAO API base URL and terminal identity in the session manifest
- **AND THEN** subsequent prompt and stop operations target the CAO terminal using only the persisted session manifest fields (no CAO base URL override)

#### Scenario: Loopback CAO runtime communication bypasses caller proxy env on a non-default port
- **WHEN** a developer starts or resumes a CAO-backed session using loopback CAO base URL `http://127.0.0.1:9991`
- **AND WHEN** caller environment includes `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY`
- **THEN** runtime-owned CAO HTTP communication bypasses those proxy endpoints by default
- **AND THEN** loopback CAO connectivity depends on local CAO availability rather than external proxy availability

#### Scenario: Preserve mode respects caller `NO_PROXY` for loopback
- **WHEN** a developer starts or resumes a CAO-backed session using a supported loopback CAO base URL
- **AND WHEN** caller environment includes `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`
- **THEN** runtime-owned CAO HTTP communication uses caller-provided proxy and `NO_PROXY` settings
