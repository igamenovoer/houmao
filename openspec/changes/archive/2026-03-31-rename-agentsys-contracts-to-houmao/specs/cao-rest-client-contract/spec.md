## MODIFIED Requirements

### Requirement: CAO REST client matches the vendored CAO API contract
The system SHALL implement a CAO-compatible REST client whose request parameter names, parameter locations, and response shapes match the pinned CAO server API contract.

For supported loopback compatibility base URLs, the CAO-compatible REST client SHALL bypass ambient proxy environment variables by default by ensuring loopback entries exist in `NO_PROXY` and `no_proxy`.

When `HOUMAO_PRESERVE_NO_PROXY_ENV=1`, the CAO-compatible REST client SHALL NOT modify `NO_PROXY` or `no_proxy` and will respect caller-provided values.

#### Scenario: Loopback compatibility requests bypass ambient proxy env on a non-default port
- **WHEN** the CAO-compatible client is configured with pair root base URL `http://127.0.0.1:9990`
- **AND WHEN** caller environment includes `HTTP_PROXY`, `HTTPS_PROXY`, or `ALL_PROXY`
- **THEN** client requests to the loopback compatibility authority bypass those proxy endpoints by default

### Requirement: CAO backend uses tmux session env for allowlisted credential propagation
When using the CAO backend, the system SHALL apply allowlisted credential environment variables by configuring a unique tmux session environment before spawning the CAO terminal into that session.

For supported loopback CAO base URLs, the tmux session environment SHALL preserve proxy variables for agent egress and SHALL include loopback entries in `NO_PROXY` and `no_proxy` by default.

When `HOUMAO_PRESERVE_NO_PROXY_ENV=1`, the system SHALL NOT modify `NO_PROXY` or `no_proxy` and will respect caller-provided values.

#### Scenario: Preserve mode does not modify tmux `NO_PROXY`
- **WHEN** the runtime launches a CAO-backed session against a supported loopback CAO base URL
- **AND WHEN** caller environment includes `HOUMAO_PRESERVE_NO_PROXY_ENV=1`
- **THEN** the created tmux session environment does not inject or modify `NO_PROXY` or `no_proxy`

