## 1. Remove Standalone Launcher Surface

- [x] 1.1 Remove the `houmao-cao-server` console script from `pyproject.toml` while keeping `houmao-server`, `houmao-passive-server`, and `houmao-mgr`.
- [x] 1.2 Delete retired standalone launcher shim modules `src/houmao/cao_cli.py` and `src/houmao/cao/tools/cao_server_launcher.py`.
- [x] 1.3 Delete the standalone launcher implementation in `src/houmao/cao/server_launcher.py`.
- [x] 1.4 Update `src/houmao/cao/__init__.py` so it exports only retained CAO-compatible models, REST client helpers, and no-proxy helpers.
- [x] 1.5 Remove the launcher config fixture under `config/cao-server-launcher/`.
- [x] 1.6 Delete standalone launcher-only tests while preserving retained no-proxy/client/model coverage.

## 2. Remove Child-CAO Server Plumbing

- [x] 2.1 Delete `src/houmao/server/child_cao.py` and remove any imports or test fixtures that reference `ChildCaoManager` or child launcher result types.
- [x] 2.2 Remove child-CAO fields and properties from `HoumaoServerConfig`, including `startup_child`, `child_startup_timeout_seconds`, derived child URL/root paths, and child launcher config paths.
- [x] 2.3 Remove `ChildCaoStatus` and always-null `child_cao` fields from `HoumaoHealthResponse` and `HoumaoCurrentInstance`.
- [x] 2.4 Remove the ignored `child_manager` constructor parameter from `HoumaoServerService`.
- [x] 2.5 Remove `--startup-child/--no-startup-child` from `houmao-server serve`, `houmao-mgr server start`, shared config builders, and detached server command replay.
- [x] 2.6 Update server and srv-ctrl tests to assert child-CAO flags and metadata are absent rather than ignored.

## 3. Preserve Retained Compatibility Behavior

- [x] 3.1 Confirm `houmao-server` still serves `/cao/*` through `CompatibilityControlCore` and the local compatibility transport.
- [x] 3.2 Confirm `houmao.cao.models`, `houmao.cao.rest_client`, and `houmao.cao.no_proxy` remain importable for retained pair clients, gateway code, passive client compatibility, and `houmao_server_rest`.
- [x] 3.3 Confirm raw external `cao_rest` runtime backend behavior is not removed in this change beyond references to the deleted standalone launcher.
- [x] 3.4 Confirm package metadata and CLI help expose retained server binaries only: `houmao-server` and `houmao-passive-server`.

## 4. Update Active Documentation

- [x] 4.1 Update README and root instruction files so they no longer list `houmao-cao-server` as a packaged deprecated entrypoint.
- [x] 4.2 Update CLI reference docs for `houmao-server serve` and `houmao-mgr server start` to remove child-startup options.
- [x] 4.3 Update system-files docs to remove standalone CAO launcher roots, launcher config files, child-CAO roots, and launcher ownership artifacts from active references.
- [x] 4.4 Keep historical CAO references only where explicitly framed as removed or archived context.

## 5. Verification

- [x] 5.1 Run focused tests for retained CAO helpers and server command surfaces.
- [x] 5.2 Run `pixi run test` or a justified narrower unit test set if full unit tests are impractical.
- [x] 5.3 Run `pixi run lint` and `pixi run typecheck`.
- [x] 5.4 Run OpenSpec status/validation for `remove-standalone-cao-launcher` and confirm the change is apply-ready.
