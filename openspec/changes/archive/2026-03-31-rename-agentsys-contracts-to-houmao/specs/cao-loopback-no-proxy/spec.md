## MODIFIED Requirements

### Requirement: Launcher loopback health probes bypass ambient proxy by default
The launcher SHALL, for supported loopback CAO base URLs (`http://localhost:<port>`, `http://127.0.0.1:<port>` with explicit ports), bypass ambient proxy environment variables by default for launcher-owned health probes by ensuring loopback entries exist in `NO_PROXY` and `no_proxy`.

When `HOUMAO_PRESERVE_NO_PROXY_ENV=1`, the launcher SHALL NOT modify `NO_PROXY` or `no_proxy` and will respect the caller-provided values.

#### Scenario: Preserve mode respects caller `NO_PROXY` for traffic-watching proxies
- **WHEN** a developer runs launcher `status` or `start` for a supported loopback CAO base URL
- **AND WHEN** caller environment includes `HOUMAO_PRESERVE_NO_PROXY_ENV=1`
- **THEN** the launcher does not inject or modify `NO_PROXY` or `no_proxy`

### Requirement: Launcher `proxy_policy=clear` preserves loopback no-proxy semantics for spawned CAO process
The launcher SHALL clear proxy variables in the spawned `cao-server` process environment when launching local `cao-server` with `proxy_policy=clear`.

By default, the launcher-managed process environment SHALL include loopback entries in `NO_PROXY` and `no_proxy`. When `HOUMAO_PRESERVE_NO_PROXY_ENV=1`, the launcher SHALL NOT modify `NO_PROXY` or `no_proxy` in the spawned process environment.

#### Scenario: Spawned CAO process has cleared proxy vars and preserve mode leaves no-proxy untouched
- **WHEN** launcher starts `cao-server` for loopback base URL `http://localhost:9991` with `proxy_policy=clear`
- **AND WHEN** caller environment includes `HOUMAO_PRESERVE_NO_PROXY_ENV=1`
- **THEN** spawned process environment does not include forwarded proxy vars
- **AND THEN** the launcher does not inject or modify `NO_PROXY` or `no_proxy`

