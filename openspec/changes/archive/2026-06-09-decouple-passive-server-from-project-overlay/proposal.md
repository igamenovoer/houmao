## Why

`houmao-passive-server` is intended to be a global coordination service for the shared registry, but the current CLI refuses to start without a Houmao project overlay when no runtime root is supplied. This blocks simple global-service usage and makes the AG-UI workbench depend on project setup even though discovery only needs the shared registry.

## What Changes

- Remove the project-overlay prerequisite from `houmao-passive-server serve`.
- Make passive-server runtime state use the global runtime root resolution path by default, with `--runtime-root` and `HOUMAO_GLOBAL_RUNTIME_DIR` still overriding it.
- Add configured passive-server registry-root support with a `--registry-root` CLI option, `HOUMAO_GLOBAL_REGISTRY_DIR` env override, and default shared-registry location.
- Route passive-server discovery and passive-server-owned registry writes/removals through the configured registry root.
- Update docs and manual validation so passive-server global-service startup is documented and tested without requiring a Houmao project overlay.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `passive-server-lifecycle`: passive-server default startup and configuration no longer require a project overlay and include explicit registry-root configuration.
- `passive-server-agent-discovery`: discovery uses the configured shared registry root rather than ambient project state.
- `docs-cli-reference`: CLI docs describe passive-server as a global service and document registry-root configuration.

## Impact

- Affects `src/houmao/passive_server/config.py`, `cli.py`, `discovery.py`, `service.py`, and `headless.py`.
- Adds or updates passive-server unit tests for root resolution, CLI startup, discovery root selection, and registry writes/removals.
- Updates passive-server CLI reference and manual validation scripts.
- Does not change public HTTP route shapes.
