# Enhancement Proposal: Remove Dead `ChildCaoManager` and Related Child-CAO Scaffolding

## Status
Proposed

## Summary
`ChildCaoManager` and the surrounding child-CAO scaffolding are dead code. Since the CAO control plane was absorbed into `houmao-server` (commit `647ffa5`), nothing in the production path starts a child `cao-server` subprocess or routes requests through one. The classes, config fields, model fields, and CLI flags that supported this pattern should be removed to reduce confusion and maintenance surface.

## Why

`houmao-server` now owns its CAO-compatible control plane natively via `CompatibilityControlCore`. All `/cao/*` HTTP requests are dispatched in-process through `LocalCompatibilityTransportBridge` → `LocalCompatibilityTransport` → `CompatibilityControlCore`. No subprocess is involved.

`ChildCaoManager` was the old mechanism that started a `cao-server` child process on a derived port (`public_port + 1`) and proxied CAO requests to it. That role no longer exists, but the class and its infrastructure were not cleaned up when the control core was absorbed. Specifically:

- `HoumaoServerService.__init__` still accepts a `child_manager: object | None` parameter and immediately discards it (`del child_manager`).
- `HoumaoServerConfig` still computes `child_api_base_url`, `child_root`, `child_runtime_root`, `child_launcher_config_path`, `child_bind_host()`, `child_startup_timeout_seconds`, and `startup_child` — none of which are used anywhere except `ChildCaoManager` itself and tests that test `ChildCaoManager`.
- `HoumaoHealthResponse` and `HoumaoCurrentInstance` both carry an optional `child_cao: ChildCaoStatus | None` field that is always `None` in the live service.
- `ChildCaoStatus` is a model class with no live producers.
- `houmao-server serve` still accepts a `--startup-child / --no-startup-child` CLI flag that has no runtime effect.
- Every test in `tests/unit/server/test_service.py` passes `child_manager=_FakeChildManager()` even though `HoumaoServerService` ignores it.
- `tests/unit/server/test_config.py` tests `child_api_base_url` and `child_root` properties that only exist to serve the removed pattern.

Keeping this scaffolding in place misleads readers into thinking a child process is still involved, and the `startup_child` config flag in particular creates false expectations about server behavior.

## Proposed Direction

### 1. Delete `src/houmao/server/child_cao.py`
The entire file — `ChildCaoManager`, `ChildCaoInstance`, `ChildCaoInstallResult`, `ChildCaoInstallError` — is unused in production. Remove it.

### 2. Remove dead fields from `HoumaoServerConfig` (`src/houmao/server/config.py`)
Remove:
- `child_startup_timeout_seconds` field
- `startup_child` field
- `child_api_base_url` property
- `child_root` property
- `child_runtime_root` property
- `child_launcher_config_path` property
- `child_bind_host()` method

### 3. Remove the `child_manager` parameter from `HoumaoServerService.__init__` (`src/houmao/server/service.py`)
Drop the parameter and the `del child_manager` line.

### 4. Remove child-CAO fields from response models (`src/houmao/server/models.py`)
- Delete `ChildCaoStatus` class.
- Remove `child_cao: ChildCaoStatus | None` from `HoumaoHealthResponse`.
- Remove `child_cao: ChildCaoStatus | None` from `HoumaoCurrentInstance`.

### 5. Remove `--startup-child / --no-startup-child` from the `serve` CLI (`src/houmao/server/commands/serve.py`)
Drop the Click option and stop passing `startup_child` to `HoumaoServerConfig`.

### 6. Clean up tests
- In `tests/unit/server/test_service.py`: remove `_FakeChildManager` and all `child_manager=_FakeChildManager()` call sites.
- In `tests/unit/server/test_config.py`: remove assertions on `child_api_base_url`, `child_root`, and related properties.
- In `tests/unit/server/test_app_contracts.py`: remove `child_cao=None` assertions and the `child_cao` field from the service doubles.

## Acceptance Criteria
1. `child_cao.py` is deleted; no production code references `ChildCaoManager`.
2. `HoumaoServerConfig` has no `child_*` fields or properties.
3. `HoumaoServerService.__init__` has no `child_manager` parameter.
4. `ChildCaoStatus`, `HoumaoHealthResponse.child_cao`, and `HoumaoCurrentInstance.child_cao` are removed.
5. `houmao-server serve --help` no longer shows `--startup-child`.
6. All tests pass after the cleanup.
7. No import of `houmao.server.child_cao` remains anywhere in `src/` or `tests/`.

## Likely Touch Points
- `src/houmao/server/child_cao.py` — delete
- `src/houmao/server/config.py` — remove `child_*` fields and properties
- `src/houmao/server/service.py` — remove `child_manager` param and `del child_manager`
- `src/houmao/server/models.py` — remove `ChildCaoStatus`, `child_cao` fields on health/instance models
- `src/houmao/server/commands/serve.py` — remove `--startup-child` option
- `tests/unit/server/test_service.py` — remove `_FakeChildManager` and all usages (~17 call sites)
- `tests/unit/server/test_config.py` — remove `child_api_base_url` / `child_root` assertions
- `tests/unit/server/test_app_contracts.py` — remove `child_cao=None` assertions and service double fields

## Non-Goals
- No change to `CompatibilityControlCore` or `LocalCompatibilityTransport` behavior.
- No change to the `cao_rest` backend (external CAO compatibility path).
- No change to `src/houmao/cao/` (the REST client, no-proxy helpers, etc.).
- No removal of `houmao-cao-server` entrypoint migration shim in `cao_cli.py` (separate concern).
