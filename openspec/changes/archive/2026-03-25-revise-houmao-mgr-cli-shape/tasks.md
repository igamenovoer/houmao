## 1. Reshape the `houmao-mgr` top-level command tree

- [x] 1.1 Update `src/houmao/srv_ctrl/commands/main.py` so the root Click group uses `invoke_without_command=True` and prints help on bare `houmao-mgr` invocation.
- [x] 1.2 Register a new `server` command group and remove the supported top-level registrations for `cao` and top-level `launch`.
- [x] 1.3 Retire or refactor command modules/helpers that only exist to expose `houmao-mgr cao *` and `houmao-mgr launch`, keeping only logic that is still needed by the new `server` or `agents` surfaces.

## 2. Add the `houmao-mgr server` lifecycle surface

- [x] 2.1 Create `src/houmao/srv_ctrl/commands/server.py` with `server start` wired to the existing `houmao-server serve` startup/configuration path and matching startup flags.
- [x] 2.2 Implement `server status` so it reports health, URL, and active-session summary, and handles the no-server-running case without a traceback.
- [x] 2.3 Implement `server sessions list`, `server sessions show`, and `server sessions shutdown` by reusing the existing Houmao server client/session APIs.
- [x] 2.4 Add the missing graceful-stop path needed for `server stop`, including any server-side shutdown route or lifecycle plumbing required for the CLI to stop a running `houmao-server`.

## 3. Move launch into `houmao-mgr agents launch`

- [x] 3.1 Add `agents launch` to `src/houmao/srv_ctrl/commands/agents/core.py` and move the established launch option validation, provider selection, and workspace-trust confirmation there.
- [x] 3.2 Replace the current server-mediated launch path with the local pipeline `resolve_native_launch_target()` -> `build_brain_home()` -> `start_runtime_session()` -> shared-registry publication.
- [x] 3.3 Support both `--headless` and interactive tmux-attached launch modes, including custom `--session-name` handling and launch success output with agent identity plus manifest path.
- [x] 3.4 Ensure unsupported providers, unresolved recipes, and failed launches exit with clear Click errors and do not leave partial runtime or registry artifacts behind.

## 4. Implement registry-first managed-agent discovery and control

- [x] 4.1 Add shared discovery helpers that resolve `agent_ref` from the live-agent registry first, then fall back to explicit `--port`, `CAO_PORT`, and the default server URL when registry lookup fails.
- [x] 4.2 Update `agents list`, `show`, `state`, `history`, `prompt`, `interrupt`, and `stop` to use registry-first discovery and route control either to `houmao-server` or directly through `RuntimeSessionController`, depending on backend type.
- [x] 4.3 Update the `agents gateway`, `agents mail`, and `agents turn` subcommands to share the same registry-first addressing model instead of assuming a server-only control path.
- [x] 4.4 Deduplicate `agents list` results when both the shared registry and a reachable server describe the same agent, while preserving `--port` as an explicit direct-server override.

## 5. Remove retired CLI surface from repo-owned references

- [x] 5.1 Update repo-owned tests, docs, and non-demo command references to use `houmao-mgr agents launch` and `houmao-mgr server *` instead of `houmao-mgr cao *` or top-level `houmao-mgr launch`.
- [x] 5.2 Keep `scripts/demo/**` migrations out of scope for this change and capture any remaining demo-command follow-ups separately instead of blocking the core CLI reshape.
- [x] 5.3 Remove or rewrite help text, migration guidance, and compatibility messaging that still describes the `cao` namespace or top-level `launch` as supported surfaces.

## 6. Verify the reshaped CLI end to end

- [x] 6.1 Add or update unit tests for root help behavior, new `server` command routing, provider validation, and registry-first discovery fallback rules.
- [x] 6.2 Add integration/runtime coverage for local `agents launch`, shared-registry discovery, and `server` lifecycle/session-management commands.
- [x] 6.3 Run `pixi run lint`, `pixi run typecheck`, `pixi run test`, and any targeted runtime suites needed to verify the new CLI shape before implementation is considered complete.
