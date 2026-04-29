## Why

The standalone CAO server launcher is already outside the supported product path, while `houmao-server` now serves the preserved `/cao/*` compatibility surface through a Houmao-owned control core. Keeping the retired launcher implementation, child-CAO configuration, and launcher-specific docs/tests makes the repository look more coupled to external CAO runtime behavior than it actually is.

## What Changes

- **BREAKING**: Remove the packaged `houmao-cao-server` console script and equivalent `houmao.cao.tools.cao_server_launcher` launcher module instead of preserving retired migration shims.
- Remove the standalone `cao-server` launcher implementation, launcher config fixture, child-CAO manager module, and launcher-only tests.
- Remove `houmao-server` startup options, config fields, models, docs, and test expectations that refer to a child `cao-server` process or `child_cao` metadata.
- Keep `houmao-server` and `houmao-passive-server` as the retained server entrypoints.
- Keep the Houmao-owned `/cao/*` compatibility namespace, CAO-compatible REST payload models/client helpers, and `houmao_server_rest` support needed by the retained server pair.
- Leave retirement of the raw external `cao_rest` runtime backend for a later change, because `houmao_server_rest` still shares code with that backend.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `cao-server-launcher`: standalone launcher surfaces are deleted rather than retained as runnable migration-guidance shims.
- `cao-loopback-no-proxy`: launcher-owned loopback health-probe and spawned-process proxy behavior is retired with the standalone launcher.
- `houmao-server`: server startup and public metadata no longer expose child-CAO process configuration, flags, or models.
- `docs-cli-reference`: CLI reference and entrypoint listings reflect that only `houmao-server` and `houmao-passive-server` remain as supported server binaries.

## Impact

- Affected package entrypoints: `pyproject.toml` script table drops `houmao-cao-server`; `houmao-server` and `houmao-passive-server` remain.
- Affected runtime code: standalone launcher modules under `houmao.cao`, child-CAO manager code under `houmao.server`, and unused child-startup plumbing are removed.
- Affected tests: launcher-specific unit/integration suites are removed or replaced with assertions around retained server surfaces; server config/command tests are updated for the smaller startup contract.
- Affected docs/specs: active docs stop describing standalone launcher invocation, launcher config files, child-CAO roots, and child-startup options as maintained surfaces.
