## REMOVED Requirements

### Requirement: Launcher loopback health probes bypass ambient proxy by default
**Reason**: Standalone launcher-owned health probes are removed with the standalone CAO server launcher.

**Migration**: Retained CAO-compatible clients and `houmao-server` internals that need loopback proxy behavior SHALL continue to use retained client-side no-proxy helpers. There is no standalone launcher probe to configure.

#### Scenario: No launcher health probe exists
- **WHEN** the standalone CAO launcher is absent
- **THEN** there is no launcher-owned `status` or `start` health probe
- **AND THEN** launcher-specific `NO_PROXY` mutation requirements no longer apply

### Requirement: Launcher `proxy_policy=clear` preserves loopback no-proxy semantics for spawned CAO process
**Reason**: The project no longer spawns a standalone child `cao-server` process through the removed launcher.

**Migration**: Provider process environment behavior for retained `houmao-server` compatibility launches SHALL be owned by the Houmao control core and provider adapters, not by standalone launcher `proxy_policy` configuration.

#### Scenario: No launcher-spawned CAO process exists
- **WHEN** `houmao-server` serves the supported compatibility surface
- **THEN** it does not spawn or manage a standalone `cao-server` process through launcher `proxy_policy`
- **AND THEN** spawned-process proxy behavior is not configured through standalone launcher TOML
