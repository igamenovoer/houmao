# Project Overlay Resolution

Use this reference when the question is how Houmao decides which `.houmao/` overlay is active for the current invocation.

## Resolution Order

- `HOUMAO_PROJECT_OVERLAY_DIR` is the strongest selector. It must be an absolute path to the overlay root itself.
- When `HOUMAO_PROJECT_OVERLAY_DIR` is unset, ambient discovery follows `HOUMAO_PROJECT_OVERLAY_DISCOVERY_MODE`.
- When nothing is discovered, the fallback candidate is `<cwd>/.houmao`.

## Discovery Modes

- `ancestor` is the default. It searches the nearest ancestor `.houmao/houmao-config.toml` from the current working directory and stops at the Git boundary.
- `cwd_only` inspects only `<cwd>/.houmao/houmao-config.toml` and skips parent overlays.

## Agent-Definition Root Precedence

When a command needs the effective agent-definition root, the current precedence is:

1. explicit CLI `--agent-def-dir`
2. `HOUMAO_AGENT_DEF_DIR`
3. selected overlay config `[paths] agent_def_dir`
4. `<overlay-root>/agents` when `HOUMAO_PROJECT_OVERLAY_DIR` points at an overlay root that is not initialized yet
5. `<cwd>/.houmao/agents`

## Bootstrap Distinction

- `project init` bootstraps the selected overlay root, using `HOUMAO_PROJECT_OVERLAY_DIR` when set and otherwise `<cwd>/.houmao`.
- `project status` uses non-creating resolution and reports `would_bootstrap_overlay` when no overlay exists yet.
- Stateful project-aware flows that ensure local roots may bootstrap the selected overlay.
- `project easy instance list|get|stop` use non-creating selected-overlay resolution and therefore require an already-existing selected overlay.
