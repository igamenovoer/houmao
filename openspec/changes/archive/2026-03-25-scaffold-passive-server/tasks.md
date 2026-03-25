## 1. Package Structure

- [x] 1.1 Create `src/houmao/passive_server/__init__.py` with module docstring
- [x] 1.2 Create `src/houmao/passive_server/config.py` with `PassiveServerConfig` Pydantic model (fields: `api_base_url` defaulting to `http://127.0.0.1:9891`, `runtime_root` from `resolve_runtime_root()`; derived properties: `server_root`, `run_dir`, `public_host`, `public_port`)
- [x] 1.3 Create `src/houmao/passive_server/models.py` with `PassiveHealthResponse` (`status`, `houmao_service="houmao-passive-server"`), `PassiveCurrentInstance` (`schema_version`, `status`, `pid`, `api_base_url`, `server_root`, `started_at_utc`), and `PassiveShutdownResponse` (`status`)

## 2. Service Layer

- [x] 2.1 Create `src/houmao/passive_server/service.py` with `PassiveServerService` class holding config, `m_started_at_utc`, and lifecycle methods `startup()` (create dirs, write `current_instance.json`) and `shutdown()` (remove `current_instance.json`)
- [x] 2.2 Implement `health()`, `current_instance()`, and `request_shutdown()` methods on the service

## 3. FastAPI Application

- [x] 3.1 Create `src/houmao/passive_server/app.py` with `create_app(config, service)` factory, lifespan handler calling `service.startup()` / `service.shutdown()`, and route definitions for `GET /health`, `GET /houmao/server/current-instance`, `POST /houmao/server/shutdown`
- [x] 3.2 Wire shutdown to send `SIGTERM` to the current process (same pattern as existing server)

## 4. CLI Entrypoint

- [x] 4.1 Create `src/houmao/passive_server/cli.py` with Click group and `serve` subcommand accepting `--host`, `--port`, `--runtime-root` options; starts uvicorn with the app factory
- [x] 4.2 Add `houmao-passive-server = "houmao.passive_server.cli:main"` to `pyproject.toml` console_scripts

## 5. Tests

- [x] 5.1 Create `tests/unit/passive_server/test_config.py` — validate `PassiveServerConfig` defaults, `api_base_url` normalization, `runtime_root` resolution, derived `server_root`
- [x] 5.2 Create `tests/unit/passive_server/test_app_contracts.py` — test `GET /health` response shape and identity, `GET /houmao/server/current-instance` response fields, `POST /houmao/server/shutdown` response; use `TestClient` from FastAPI
- [x] 5.3 Create `tests/unit/passive_server/test_service.py` — test `startup()` creates `current_instance.json` at expected path, `shutdown()` removes it, `current_instance()` returns correct PID and URL

## 6. Verification

- [x] 6.1 Run `pixi run lint` and `pixi run typecheck` with no new errors in `src/houmao/passive_server/`
- [x] 6.2 Run `pixi run test` and confirm all new tests pass
- [x] 6.3 Manual smoke test: `houmao-passive-server serve`, then `curl localhost:9891/health` returns expected response
