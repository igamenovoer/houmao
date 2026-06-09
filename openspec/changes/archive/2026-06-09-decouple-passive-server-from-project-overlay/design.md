## Context

`houmao-passive-server` is the maintained server/API authority for global agent discovery and management. Its discovery model reads the shared registry, which already has a global default root through `resolve_registry_root()`. Its own durable state also has a global default root through `resolve_runtime_root()`.

The current CLI startup path adds an unnecessary project-overlay guard when no `--runtime-root` is provided. That means a global service cannot start from an arbitrary directory, even though most passive-server route families only need concrete runtime and registry roots. This also makes AG-UI discovery harder to test because the GUI expects passive-server to be a global discovery service, not a project-local command.

## Goals / Non-Goals

**Goals:**

- Allow `houmao-passive-server serve` to start without a Houmao project overlay.
- Keep runtime-root selection explicit and predictable: CLI override, env override, then global default.
- Add first-class passive-server registry-root configuration through `PassiveServerConfig`, `--registry-root`, and `HOUMAO_GLOBAL_REGISTRY_DIR`.
- Ensure passive-server discovery and passive-server-owned registry writes/removals use the same configured registry root.
- Update docs and manual validation to reflect passive-server as a global service.

**Non-Goals:**

- Do not change HTTP route shapes or response schemas.
- Do not change project-aware `houmao-mgr` commands.
- Do not change the shared registry storage layout.
- Do not introduce a new daemon supervisor or service manager.

## Decisions

1. Default passive-server runtime root uses `resolve_runtime_root()`.

   Passive-server-owned state is global service state. The default should follow the same explicit, env, default ordering used by `owned_paths.resolve_runtime_root()` rather than requiring a selected project overlay. Project-local runtime roots remain available by passing `--runtime-root` or `HOUMAO_GLOBAL_RUNTIME_DIR`.

2. Add `registry_root` to `PassiveServerConfig`.

   Discovery already says it scans the configured registry root, but the implementation currently reads ambient registry helpers with no config value. Adding `registry_root` makes the server's read/write registry target explicit and testable.

3. Add `--registry-root` to `houmao-passive-server serve`.

   CI, demos, and manual validation need isolated registries. The env var `HOUMAO_GLOBAL_REGISTRY_DIR` remains the normal non-CLI override, and the default remains the platformdirs-backed shared registry root.

4. Bridge configured root into existing registry helpers.

   The registry storage APIs already accept an `env` mapping. Passive-server code should pass a small mapping such as `{"HOUMAO_GLOBAL_REGISTRY_DIR": str(config.registry_root)}` to discovery, publish, and remove calls instead of rewriting registry storage.

5. Keep passive-server-owned stop semantics intact.

   `stop_agent()` and `HeadlessAgentService.stop_managed()` currently remove registry records for agents they stop. This change does not reclassify those operations; it only ensures they use the configured registry root.

## Risks / Trade-offs

- Existing tests that assumed project-aware defaults may fail -> update passive-server tests to assert global defaults instead.
- Running a server with a custom runtime root but default registry root may surprise CI users -> docs and manual tests should pass both roots when isolation matters.
- Ambient manager launches and passive-server may point at different registry roots if only one side overrides env -> docs should state that agents are discoverable only when both sides use the same shared registry root.
- Changing default startup behavior could write server state under the global runtime root from any directory -> this matches the intended global-service model, and explicit `--runtime-root` remains available for isolation.

## Migration Plan

No migration is required for existing stored data. Existing users who pass `--runtime-root` keep the same behavior. Users who relied on implicit project-overlay runtime selection should now pass the project runtime root explicitly or set `HOUMAO_GLOBAL_RUNTIME_DIR` before starting passive-server.
