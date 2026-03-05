## MODIFIED Requirements

### Requirement: Optional CAO backend via REST boundary
The system SHALL optionally support launching and driving sessions via CAO
using CAO's REST API, without requiring the core runtime to depend on CAO
internals.

For supported loopback CAO base URLs (`http://localhost:9889`,
`http://127.0.0.1:9889`), runtime-owned CAO HTTP communication SHALL bypass
ambient proxy environment variables by default by ensuring loopback entries
exist in `NO_PROXY`/`no_proxy`.

When `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`, the runtime SHALL NOT modify `NO_PROXY`
or `no_proxy` and will respect caller-provided values (for example, to enable
traffic-watching development proxies).

#### Scenario: CAO-backed session launch and messaging
- **WHEN** a developer starts a CAO-backed session and provides a CAO API base URL at session start
- **THEN** the system creates a CAO session/terminal, sends prompts, and fetches replies using CAO REST endpoints
- **AND THEN** the system persists the CAO API base URL and terminal identity in the session manifest
- **AND THEN** subsequent prompt and stop operations target the CAO terminal using only the persisted session manifest fields (no CAO base URL override)

#### Scenario: Loopback CAO runtime communication bypasses caller proxy env
- **WHEN** a developer starts or resumes a CAO-backed session using a supported loopback CAO base URL
- **AND WHEN** caller environment includes `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY`
- **THEN** runtime-owned CAO HTTP communication bypasses those proxy endpoints by default
- **AND THEN** loopback CAO connectivity depends on local CAO availability rather than external proxy availability

#### Scenario: Preserve mode respects caller `NO_PROXY` for loopback
- **WHEN** a developer starts or resumes a CAO-backed session using a supported loopback CAO base URL
- **AND WHEN** caller environment includes `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`
- **THEN** runtime-owned CAO HTTP communication uses caller-provided proxy and `NO_PROXY` settings

## ADDED Requirements

### Requirement: Runtime-launched agent subprocess env injects loopback `NO_PROXY` by default
The runtime SHALL, when launching agent backends via subprocess (for example,
Codex app-server and Claude/Gemini headless CLIs), preserve proxy variables for
agent egress and SHALL, by default, ensure loopback entries exist in `NO_PROXY`
and `no_proxy` (merge+append semantics; entries include `localhost`,
`127.0.0.1`, and `::1`).

When `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`, the runtime SHALL NOT modify `NO_PROXY`
or `no_proxy` for the spawned process and will respect caller-provided values.

#### Scenario: Non-CAO backend subprocess env injects loopback `NO_PROXY` by default
- **WHEN** a developer launches a non-CAO backend session (for example, Codex app-server or a headless CLI)
- **AND WHEN** caller environment includes `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY`
- **THEN** the runtime-launched backend subprocess environment includes loopback `NO_PROXY`/`no_proxy` entries by default

#### Scenario: Preserve mode does not modify non-CAO subprocess `NO_PROXY`
- **WHEN** a developer launches a non-CAO backend session
- **AND WHEN** caller environment includes `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`
- **THEN** the runtime does not inject or modify `NO_PROXY`/`no_proxy` for the spawned backend process
