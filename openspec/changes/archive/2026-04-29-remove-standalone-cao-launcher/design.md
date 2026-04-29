## Context

`houmao-server` has absorbed the supported CAO-compatible control surface into a Houmao-owned native control core. The live server path already dispatches `/cao/*` through `CompatibilityControlCore` and a local transport, while `HoumaoServerService` ignores the injected `child_manager` argument and returns no `child_cao` metadata in health or current-instance payloads.

The remaining standalone launcher surface is therefore mostly repository drag:

- `houmao-cao-server` is a packaged console script that only prints retirement guidance.
- `houmao.cao.tools.cao_server_launcher` is a module shim that only prints retirement guidance.
- `houmao.cao.server_launcher` still contains the old detached `cao-server` lifecycle implementation.
- `houmao.server.child_cao` still wraps that launcher implementation even though `houmao-server` no longer uses it.
- `HoumaoServerConfig` and server startup commands still expose child-startup fields and flags that no longer affect behavior.
- Active docs and specs still mention standalone launcher files, child roots, and launcher proxy behavior as if they were maintained surfaces.

The supported server entrypoints after this change are `houmao-server` and `houmao-passive-server`. The supported management CLI remains `houmao-mgr`.

## Goals / Non-Goals

**Goals:**

- Remove the standalone `cao-server` launcher implementation and its package entrypoints.
- Remove child-CAO configuration, CLI flags, models, docs, and tests from the retained server code.
- Preserve the `houmao-server` pair contract, including `/cao/*` compatibility routes backed by the native control core.
- Preserve CAO-compatible REST payload models, client helpers, and loopback no-proxy helpers that are still used by `houmao-server`, pair clients, gateways, and `houmao_server_rest`.
- Update active docs/specs so operators see only `houmao-server` and `houmao-passive-server` as server binaries.

**Non-Goals:**

- Do not remove the `houmao-server` `/cao/*` compatibility namespace.
- Do not remove `houmao_server_rest` or refactor its shared code with `cao_rest` in this change.
- Do not remove raw `cao_rest` backend literals or persisted-manifest support yet; that requires a separate runtime compatibility cutover.
- Do not rename every internal `Cao*` type that currently represents compatibility payloads.

## Decisions

1. Delete the retired launcher entrypoint instead of keeping a failure shim.

   The repository is still unstable and allows breaking changes. Removing the console script and module entrypoint makes the package contract match the stated retained server surface. The alternative was to keep the migration shims indefinitely, but that preserves the idea that `houmao-cao-server` is still a maintained binary.

2. Treat `houmao.cao.server_launcher` as launcher-only code.

   The implementation owns detached process management, pid files, ownership files, and spawned-process proxy policy. Those responsibilities belong to the removed standalone launcher, not the retained pair. Shared no-proxy behavior remains in `houmao.cao.no_proxy`; shared compatibility payload behavior remains in `houmao.cao.models` and `houmao.cao.rest_client`.

3. Remove child-CAO server config from `houmao-server` instead of making it a no-op.

   `startup_child`, `child_startup_timeout_seconds`, `child_api_base_url`, `child_root`, `child_runtime_root`, and `child_launcher_config_path` no longer represent active behavior. Keeping them as accepted options creates false operational affordances and complicates tests. The retained compatibility startup timing options stay because the native control core still uses them for provider readiness behavior.

4. Keep `/cao/*` route handling local to `houmao-server`.

   The compatibility namespace is still required by the supported pair and current specs. This change narrows CAO removal to the external runtime dependency and retired launcher surfaces, not to the HTTP compatibility contract.

5. Scope raw `cao_rest` backend retirement out of this change.

   `houmao_server_rest` currently subclasses `CaoRestSession`, and gateway/runtime tests still rely on shared session-backed behavior. Removing raw `cao_rest` safely should first split or rename the shared session-backed core so `houmao_server_rest` is not coupled to the public raw backend name.

## Risks / Trade-offs

- Operators or scripts that invoke `houmao-cao-server` will now fail at command lookup rather than receiving migration guidance -> Update active docs and release notes to direct users to `houmao-mgr server start`, `houmao-server serve`, or `houmao-passive-server serve`.
- Deleting launcher code can accidentally remove helpers still used by retained clients -> Keep `houmao.cao.no_proxy`, `houmao.cao.models`, and `houmao.cao.rest_client`, and move or preserve tests for those retained helpers.
- Removing child-startup flags can break automation that still passes `--startup-child` -> Treat this as an intentional breaking cleanup and update detached server replay plus tests so the option is absent from the live help.
- Historical specs may still describe CAO-era behavior -> Update current capability specs and active docs; leave archived changes untouched.

## Migration Plan

1. Remove the package entrypoint and launcher modules.
2. Remove child-CAO config/model/CLI plumbing from `houmao-server` and `houmao-mgr server start`.
3. Update tests to assert the retained server entrypoints and the absence of child-CAO flags/metadata.
4. Update active docs and system-files references to remove standalone launcher roots and config files.
5. Run focused unit tests for `server`, `srv_ctrl`, retained `cao` helpers, and full unit tests if practical.

Rollback would restore the deleted entrypoint and launcher modules from version control. No runtime data migration is required because the launcher artifacts are already outside the supported server state.

## Open Questions

- When should the raw external `cao_rest` backend be removed or renamed behind a Houmao-owned session-backed implementation?
- Should retained CAO-compatible payload/client modules eventually move from `houmao.cao` to a `houmao.compat` namespace after `cao_rest` retirement?
