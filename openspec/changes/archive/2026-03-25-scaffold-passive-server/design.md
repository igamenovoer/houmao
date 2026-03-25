## Context

The current `houmao-server` is a ~3500-line FastAPI application tightly coupled to CAO compatibility: a `CompatibilityControlCore`, a supervised child CAO process, registration-backed TUI admission, and a full `/cao/*` route surface. The target distributed-agent architecture calls for a server that discovers agents from the shared filesystem registry and acts as an optional coordination layer, not as a session-creation authority.

The greenfield migration path (`context/design/future/distributed-agent-migration-path-greenfield.md`) defines 8 steps. This change covers Step 1: scaffold the new `houmao-passive-server` package with the application factory, configuration, and server lifecycle endpoints. Subsequent changes will add discovery, observation, gateway proxy, and headless management on top of this scaffold.

## Goals / Non-Goals

**Goals:**
- Create a new `src/houmao/passive_server/` package that can be developed and tested independently of the existing server.
- Provide a FastAPI application factory (`create_app()`) with lifespan management following the same pattern as the existing server.
- Define a `PassiveServerConfig` model with only the fields needed for the passive server (no CAO/compat fields).
- Implement the three server lifecycle endpoints: health, current-instance, and shutdown.
- Wire a `houmao-passive-server` CLI entrypoint via `pyproject.toml` console_scripts.
- Ensure the passive server can run alongside the existing server on a different port.

**Non-Goals:**
- Agent discovery, TUI observation, gateway proxy, headless management, or any `/cao/*` routes. These are future steps.
- Modifying, deprecating, or removing the existing `houmao-server` package.
- Shared code extraction or refactoring of existing modules.

## Decisions

### Decision 1: Separate package, not a mode flag

Create `src/houmao/passive_server/` as a fully independent package rather than adding a `--mode passive` flag to the existing server.

**Rationale:** A mode flag would couple the new server's lifecycle to the existing server's import graph, pulling in CAO compatibility, child process management, and registration models. A separate package guarantees a clean dependency boundary. The package can be renamed to `src/houmao/server/` when the old server is retired.

**Alternative considered:** `--mode passive` on the existing CLI. Rejected because it defeats the purpose of a clean-break migration.

### Decision 2: Default port 9891

The passive server defaults to `http://127.0.0.1:9891`, avoiding collision with the existing server's default port `9889` and its child CAO on `9890`.

**Rationale:** Both servers must be runnable simultaneously during the parallel validation period.

### Decision 3: Health response identifies as `houmao-passive-server`

The health endpoint returns `{"status": "ok", "houmao_service": "houmao-passive-server"}`. It does not extend `CaoHealthResponse` and does not include `service: "cli-agent-orchestrator"` or `child_cao` fields.

**Rationale:** The passive server is not CAO-compatible. Its health contract should reflect its own identity cleanly. Clients that need to distinguish the two servers can check `houmao_service`.

### Decision 4: Click CLI with `serve` as the primary command

Follow the existing server's CLI pattern: a Click group with a `serve` subcommand that starts uvicorn. Additional subcommands (health query, current-instance query) can be added later.

**Rationale:** Consistency with the existing server CLI. Users familiar with `houmao-server serve` will expect the same from `houmao-passive-server serve`.

### Decision 5: Minimal `PassiveServerConfig`

The config model includes only:
- `api_base_url` (default `http://127.0.0.1:9891`)
- `runtime_root` (from `resolve_runtime_root()`)

Future steps will add fields like `discovery_poll_interval_seconds`, `watch_poll_interval_seconds`, etc. as those capabilities are implemented. The scaffold config stays minimal.

**Rationale:** Avoid speculative configuration. Each field should be added when the code that uses it is implemented.

### Decision 6: `PassiveServerService` as a thin shell

The service class holds the config and exposes `startup()` / `shutdown()` lifecycle hooks. In this step, startup only writes `current_instance.json` and shutdown is a no-op cleanup. The service is the extension point for future discovery, observation, and headless services.

**Rationale:** Matches the existing server's `HoumaoServerService` pattern but without any domain logic. Provides a clean place for future steps to plug in.

## Risks / Trade-offs

**[Parallel entrypoint maintenance]** Two CLI entrypoints (`houmao-server` and `houmao-passive-server`) coexist. Users may be confused about which to use. **Mitigation:** Document that `houmao-passive-server` is experimental. At switchover (Step 8), rename and remove the old entrypoint.

**[Config divergence]** `PassiveServerConfig` and `HoumaoServerConfig` will share some fields (runtime_root, api_base_url). No shared base class is introduced. **Mitigation:** Acceptable for the transition period. At Step 8, only one config remains.

**[Empty scaffold]** The passive server does nothing useful until Step 2 (discovery). This step's value is purely structural. **Mitigation:** Step 2 should follow immediately.
