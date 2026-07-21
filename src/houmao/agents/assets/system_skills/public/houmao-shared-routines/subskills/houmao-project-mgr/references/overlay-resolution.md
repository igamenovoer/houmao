# Project Overlay Resolution

Use this reference when the question is how Houmao decides which `.houmao/` overlay is active for the current invocation.

## Resolution Order

- `HOUMAO_PROJECT_OVERLAY_DIR` is the strongest selector. It must be an absolute path to the overlay root itself.
- When `HOUMAO_PROJECT_OVERLAY_DIR` is unset, ambient discovery follows `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`.
- When nothing is discovered, the fallback candidate is `<cwd>/.houmao`.

## Discovery Modes

- `ancestor` is the default. It searches the nearest ancestor `.houmao/houmao-config.toml` from the current working directory and stops at the Git boundary.
- `cwd_only` inspects only `<cwd>/.houmao/houmao-config.toml` and skips parent overlays.

## Native Projection Root

Project commands use the selected project overlay as the project context. When a project command needs native-agent compatibility material, it projects catalog-backed specialists and profiles into the selected overlay's configured native projection root:

1. selected overlay config `[paths] agent_def_dir`
2. `<overlay-root>/agents`

Direct native-agent work does not use project overlay discovery. Use `houmao-mgr internals native-agent ... --native-agent-root <path>` or `HOUMAO_NATIVE_AGENT_ROOT` only when the user explicitly asks for provider-aligned native-agent material.

## Bootstrap Distinction

- `project init` bootstraps the selected overlay root, using `HOUMAO_PROJECT_OVERLAY_DIR` when set and otherwise `<cwd>/.houmao`.
- `project status` uses non-creating resolution and reports `would_bootstrap_overlay` when no overlay exists yet.
- Stateful project-aware flows that ensure local roots require an initialized selected overlay.
- `project agents list|get|stop` use non-creating selected-overlay resolution and therefore require an already-existing selected overlay.
