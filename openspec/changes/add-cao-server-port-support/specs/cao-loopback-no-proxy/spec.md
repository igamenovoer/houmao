## MODIFIED Requirements

### Requirement: Launcher loopback health probes bypass ambient proxy by default
The launcher SHALL, for supported loopback CAO base URLs
(`http://localhost:<port>`, `http://127.0.0.1:<port>` with explicit ports),
bypass ambient proxy environment variables by default for launcher-owned health
probes by ensuring loopback entries exist in `NO_PROXY`/`no_proxy`.

When `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`, the launcher SHALL NOT modify
`NO_PROXY` or `no_proxy` and will respect the caller-provided values (for
example, to enable traffic-watching development proxies).

#### Scenario: `status` probes loopback directly even when caller proxy vars are set
- **WHEN** a developer runs launcher `status` for a supported loopback CAO base URL
- **AND WHEN** caller environment includes `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY`
- **THEN** the launcher health probe connects directly to loopback CAO
- **AND THEN** the probe result is not routed through those proxy endpoints

#### Scenario: `start` startup polling probes loopback directly even when caller proxy vars are set
- **WHEN** a developer runs launcher `start` for loopback CAO base URL `http://127.0.0.1:9991`
- **AND WHEN** caller environment includes `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY`
- **THEN** launcher startup polling probes connect directly to loopback CAO
- **AND THEN** startup success or failure reflects loopback server health at that requested port rather than proxy reachability

#### Scenario: Preserve mode respects caller `NO_PROXY` for traffic-watching proxies
- **WHEN** a developer runs launcher `status` or `start` for a supported loopback CAO base URL
- **AND WHEN** caller environment includes `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`
- **THEN** the launcher does not inject or modify `NO_PROXY`/`no_proxy`
- **AND THEN** proxy routing behavior for loopback depends on the caller-provided proxy env values

### Requirement: Launcher `proxy_policy=clear` preserves loopback no-proxy semantics for spawned CAO process
The launcher SHALL clear proxy variables in the spawned `cao-server` process
environment when launching local `cao-server` with `proxy_policy=clear`.

By default, the launcher-managed process environment SHALL include loopback
entries in `NO_PROXY`/`no_proxy` (merge+append semantics). When
`AGENTSYS_PRESERVE_NO_PROXY_ENV=1`, the launcher SHALL NOT modify `NO_PROXY` or
`no_proxy` in the spawned process environment.

#### Scenario: Spawned CAO process has proxy vars cleared and loopback NO_PROXY entries on a non-default port
- **WHEN** launcher starts `cao-server` for loopback base URL `http://localhost:9991` with `proxy_policy=clear`
- **THEN** spawned process environment does not include `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY` (including lowercase variants)
- **AND THEN** spawned process environment includes `NO_PROXY` and `no_proxy` entries covering `localhost`, `127.0.0.1`, and `::1` unless `AGENTSYS_PRESERVE_NO_PROXY_ENV=1`
