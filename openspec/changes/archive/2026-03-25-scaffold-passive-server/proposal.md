## Why

The current `houmao-server` is deeply coupled to CAO compatibility — a `CompatibilityControlCore`, a child CAO process supervisor, registration-backed TUI admission, and `/cao/*` route handlers. The target distributed-agent architecture (see `context/design/future/distributed-agent-architecture.md`) needs a server that discovers agents from the shared registry rather than creating them. Rather than incrementally gutting the existing server, this change creates a new `houmao-passive-server` package — a clean, minimal FastAPI application that implements only registry-driven discovery, agent listing, and server lifecycle. This is Step 1 of the greenfield migration path described in `context/design/future/distributed-agent-migration-path-greenfield.md`.

## What Changes

- New Python package `src/houmao/passive_server/` containing a FastAPI application factory, server configuration model, and a stub service layer.
- New CLI entrypoint `houmao-passive-server` that starts the passive server on a configurable port.
- `PassiveServerConfig` Pydantic model with minimal fields: listen address, runtime root, registry root, poll intervals.
- Health (`GET /health`), current-instance (`GET /houmao/server/current-instance`), and shutdown (`POST /houmao/server/shutdown`) endpoints — the server lifecycle surface.
- No agent discovery, TUI observation, gateway proxy, headless management, or any `/cao/*` routes in this step. Those are subsequent steps in the migration path.
- The existing `houmao-server` is untouched. Both servers can coexist on different ports.

## Capabilities

### New Capabilities
- `passive-server-lifecycle`: Server startup, health check, current-instance query, and graceful shutdown for the new passive server. Covers the FastAPI application factory, configuration model, CLI entrypoint, and the three lifecycle endpoints.

### Modified Capabilities

(none)

## Impact

- **New package:** `src/houmao/passive_server/` (~5 files: `__init__.py`, `app.py`, `config.py`, `service.py`, `models.py`).
- **New CLI entrypoint:** `houmao-passive-server` wired through `pyproject.toml` console_scripts.
- **Dependencies:** FastAPI, uvicorn, Pydantic v2 (already project dependencies). No new external dependencies.
- **Existing code:** No modifications to `src/houmao/server/` or any other existing package.
- **Tests:** New unit tests under `tests/unit/passive_server/`.
