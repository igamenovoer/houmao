## 1. Configuration and CLI

- [x] 1.1 Update `PassiveServerConfig` so `runtime_root` defaults through `resolve_runtime_root()` instead of project-aware overlay resolution.
- [x] 1.2 Add `registry_root` to `PassiveServerConfig`, defaulting through `resolve_registry_root()` and validating to an absolute resolved path.
- [x] 1.3 Remove the `ensure_project_aware_local_roots()` startup guard from `houmao-passive-server serve`.
- [x] 1.4 Add a `--registry-root` option to `houmao-passive-server serve` and pass it into `PassiveServerConfig`.

## 2. Registry-Root Plumbing

- [x] 2.1 Add a small passive-server helper or config method that builds the registry helper env mapping from `PassiveServerConfig.registry_root`.
- [x] 2.2 Update `RegistryDiscoveryService` to scan `config.registry_root` rather than ambient registry resolution.
- [x] 2.3 Update passive-server-owned registry publications in `HeadlessAgentService` to use `config.registry_root`.
- [x] 2.4 Update passive-server-owned registry removals in `HeadlessAgentService` and `PassiveServerService.stop_agent()` to use `config.registry_root`.

## 3. Tests

- [x] 3.1 Update passive-server config tests for global default runtime and registry roots with no project overlay.
- [x] 3.2 Add or update CLI tests proving `houmao-passive-server serve` no longer fails without a project overlay.
- [x] 3.3 Add or update discovery tests proving a custom `registry_root` controls which records are discovered.
- [x] 3.4 Add or update headless/service tests proving registry publish and remove calls use the configured registry root.
- [x] 3.5 Update the passive-server manual lifecycle script to start without `--runtime-root` while still isolating state through env roots.

## 4. Documentation

- [x] 4.1 Update `docs/reference/cli/houmao-passive-server.md` to describe passive-server as a global service over the shared registry.
- [x] 4.2 Document `--registry-root`, `HOUMAO_GLOBAL_REGISTRY_DIR`, `--runtime-root`, and `HOUMAO_GLOBAL_RUNTIME_DIR` root precedence.
- [x] 4.3 Clarify that agents are discoverable only when their launching authority and passive-server use the same shared registry root.

## 5. Verification

- [x] 5.1 Run `pixi run python -m pytest tests/unit/passive_server`.
- [x] 5.2 Run the passive-server manual lifecycle and discovery scripts.
- [x] 5.3 Run `openspec validate "decouple-passive-server-from-project-overlay" --strict`.
