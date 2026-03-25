## Context

The `houmao-mgr` CLI currently has overlapping launch paths (`cao launch`, top-level `launch`, `launch --headless`) with unclear boundaries between server lifecycle management and agent lifecycle management. Agent launch always routes through `houmao-server`, even though the core pipeline (select recipe → build brain → start session → publish registry) is inherently local. The `agents` group has no `launch` command, and the `cao` group duplicates functionality with confusing naming. Invoking `houmao-mgr` without arguments raises a Python exception.

The shared registry (`~/.houmao/registry/live_agents/`) already tracks live agents with backend type, tool, manifest path, and terminal info — everything needed for post-launch discovery. However, `houmao-mgr agents` commands currently require `--port` to find the server rather than using the registry.

Key existing components that this change composes:
- `resolve_native_launch_target()` — selector → recipe resolution
- `build_brain_home()` — recipe → built brain home + manifest
- `start_runtime_session()` — manifest → RuntimeSessionController + registry record
- `LiveAgentRegistryRecordV2` — shared registry record with full agent metadata
- `houmao-server serve` — separate binary for server startup

## Goals / Non-Goals

**Goals:**

- Clear separation: `houmao-mgr server *` for server lifecycle, `houmao-mgr agents *` for agent lifecycle.
- `houmao-mgr agents launch` works without `houmao-server` by calling `start_runtime_session()` directly.
- Post-launch agent commands discover backend type and server URL from the shared registry instead of requiring `--port`.
- `houmao-mgr server start` absorbs `houmao-server serve` as the recommended entry point.
- `houmao-mgr` (no args) prints help.
- `houmao-mgr cao` group is retired.

**Non-Goals:**

- Changing the brain building pipeline itself (`BuildRequest`, `BrainBuilder`, `ToolAdapter` internals).
- Modifying the shared registry schema — `LiveAgentRegistryRecordV2` is sufficient as-is.
- Changing `houmao-server` internals or its HTTP API surface.
- Retiring the `houmao-server` binary entry point (keep for backward compat, just not recommended).
- Implementing new backends — `agents launch` uses existing `claude_headless`, `codex_headless`, `gemini_headless` backends for headless mode, and `tmux_runtime` primitives for TUI mode.

## Decisions

### D1: `agents launch` calls `start_runtime_session()` directly — no server detour

**Decision**: The new `agents launch` command performs brain building and session startup entirely client-side by calling `resolve_native_launch_target()` → `build_brain_home()` → `start_runtime_session()`. This is the same path that `materialize_headless_launch_request()` already uses for `launch --headless`, but exposed as a proper CLI command under `agents`.

**Alternatives considered**:
- *Keep server-mediated launch*: Rejected because the server adds no value during brain building — it just proxies the same `build_brain_home()` call. The server's value is in TUI tracking and managed-agent lifecycle, which can be registered after launch via the shared registry.
- *Hybrid: build locally, register with server*: Considered, but deferred. The shared registry already provides discovery. Server registration can be added later as an optional enrichment step.

**Rationale**: The existing `start_runtime_session()` path already handles brain manifest loading, launch plan building, backend session creation, and registry publication. It is the canonical local launch path. Wrapping it in a CLI command is straightforward.

### D2: TUI mode for `agents launch` uses existing headless backends with tmux attach

**Decision**: For interactive (non-headless) mode, `agents launch` starts a headless backend session in a tmux session, then attaches to that tmux session. This reuses existing `tmux_runtime` primitives and the headless session runner without requiring a new TUI backend.

**Alternatives considered**:
- *New dedicated TUI backend*: Rejected for now — adds complexity without clear benefit when tmux attach already works.
- *Require server for TUI*: Rejected — contradicts the goal of server-independent agent launch.

### D3: Registry-first discovery for post-launch commands

**Decision**: `houmao-mgr agents prompt/stop/show/etc.` resolve `<agent_ref>` by looking up the shared registry first. The registry record contains `identity.backend` and `runtime.manifest_path`, which determines whether to:
- Contact the server (backend == `houmao_server_rest` → extract `api_base_url` from manifest backend state)
- Control directly (backend == `claude_headless` etc. → use `RuntimeSessionController` via manifest)

The `--port` flag remains as an optional override but is no longer required.

**Alternatives considered**:
- *Server-only discovery*: Rejected — defeats the purpose of server-independent agents.
- *Environment variable for server URL*: Already exists (`CAO_PORT`), but registry-first is more robust and agent-specific.

### D4: `server` group absorbs `houmao-server serve` functionality

**Decision**: `houmao-mgr server start` starts the server process (via the same uvicorn startup path that `houmao-server serve` uses). `houmao-mgr server stop` sends a shutdown signal. `houmao-mgr server status` checks health and lists sessions.

The `houmao-server` binary remains as a backward-compatible entry point but documentation switches to `houmao-mgr server start`.

### D5: Hard retirement of `cao` group

**Decision**: Remove the `cao` group entirely in one step rather than a deprecation period. The `cao` commands were internal tooling, not a public API. Any remaining `cao flow` functionality is deferred — it can be reintroduced under a different namespace if needed.

**Alternatives considered**:
- *Deprecation warnings*: Rejected because `cao` is internal tooling with no external consumers. A clean cut is simpler.

### D6: Root group uses `invoke_without_command=True`

**Decision**: The Click root group is configured with `invoke_without_command=True` and a callback that prints help when no subcommand is given. This is standard Click practice.

## Proposed CLI Shape

### Before (current)

```
houmao-mgr
├── cao                                          # CAO compat namespace
│   ├── launch                                   # TUI session via server
│   │   --agents, --session-name, --headless,
│   │   --provider, --port, --yolo,
│   │   --compat-http-timeout-seconds,
│   │   --compat-create-timeout-seconds
│   ├── info                                     # session info
│   ├── init                                     # local compat init
│   ├── mcp-server                               # retired stub
│   ├── shutdown                                 # kill sessions
│   │   --all, --session, --port
│   └── flow                                     # scheduled flows
│       ├── list
│       ├── add <file_path>
│       ├── remove <name>
│       ├── disable <name>
│       ├── enable <name>
│       └── run <name>
│
├── launch                                       # top-level, overlaps cao launch
│   --agents, --session-name, --headless,
│   --provider, --port, --yolo,
│   --compat-http-timeout-seconds,
│   --compat-create-timeout-seconds
│
├── agents                                       # NO launch — post-launch only
│   ├── list
│   ├── show <agent_ref>
│   ├── state <agent_ref>
│   ├── history <agent_ref>  --limit
│   ├── prompt <agent_ref>  --prompt
│   ├── interrupt <agent_ref>
│   ├── stop <agent_ref>
│   ├── gateway
│   │   ├── attach [agent_ref]
│   │   ├── detach <agent_ref>
│   │   ├── status <agent_ref>
│   │   ├── prompt <agent_ref>  --prompt
│   │   └── interrupt <agent_ref>
│   ├── mail
│   │   ├── status <agent_ref>
│   │   ├── check <agent_ref>  --unread-only, --limit, --since
│   │   ├── send <agent_ref>  --to, --cc, --subject, --body-content, --body-file, --attach
│   │   └── reply <agent_ref>  --message-ref, --body-content, --body-file, --attach
│   └── turn
│       ├── submit <agent_ref>  --prompt
│       ├── status <agent_ref> <turn_id>
│       ├── events <agent_ref> <turn_id>
│       ├── stdout <agent_ref> <turn_id>
│       └── stderr <agent_ref> <turn_id>
│
├── brains
│   └── build
│       --agent-def-dir, --tool, --skill, --config-profile,
│       --cred-profile, --recipe, --runtime-root, --home-id,
│       --reuse-home, --launch-overrides, --agent-name, --agent-id
│
└── admin
    └── cleanup-registry  --grace-seconds
```

### After (proposed)

```
houmao-mgr                                      # no args → prints help
│
├── server                                       # NEW: server lifecycle
│   ├── start                                    # absorbs houmao-server serve
│   │   --port, --runtime-root,
│   │   --api-base-url,
│   │   [all houmao-server serve flags]
│   ├── stop                                     # graceful shutdown
│   │   --port
│   ├── status                                   # health + summary
│   │   --port
│   └── sessions                                 # server-owned sessions
│       ├── list
│       │   --port
│       ├── show <session>
│       │   --port
│       └── shutdown
│           --all | --session <name>
│           --port
│
├── agents                                       # EXPANDED: full agent lifecycle
│   ├── launch                                   # NEW: local brain build + launch
│   │   --agents (required),                     #   native launch selector
│   │   --provider (default: claude_code),       #   provider identifier
│   │   --session-name,                          #   optional tmux session name
│   │   --headless,                              #   detached mode
│   │   --yolo                                   #   skip trust confirmation
│   ├── list                                     # registry-first discovery
│   │   --port (optional override)
│   ├── show <agent_ref>                         # registry-first discovery
│   │   --port (optional override)
│   ├── state <agent_ref>
│   │   --port (optional override)
│   ├── history <agent_ref>  --limit
│   │   --port (optional override)
│   ├── prompt <agent_ref>  --prompt
│   │   --port (optional override)
│   ├── interrupt <agent_ref>
│   │   --port (optional override)
│   ├── stop <agent_ref>
│   │   --port (optional override)
│   ├── gateway                                  # unchanged subgroup
│   │   ├── attach [agent_ref]
│   │   ├── detach <agent_ref>
│   │   ├── status <agent_ref>
│   │   ├── prompt <agent_ref>  --prompt
│   │   └── interrupt <agent_ref>
│   ├── mail                                     # unchanged subgroup
│   │   ├── status <agent_ref>
│   │   ├── check <agent_ref>  --unread-only, --limit, --since
│   │   ├── send <agent_ref>  --to, --cc, --subject, --body-content, --body-file, --attach
│   │   └── reply <agent_ref>  --message-ref, --body-content, --body-file, --attach
│   └── turn                                     # unchanged subgroup
│       ├── submit <agent_ref>  --prompt
│       ├── status <agent_ref> <turn_id>
│       ├── events <agent_ref> <turn_id>
│       ├── stdout <agent_ref> <turn_id>
│       └── stderr <agent_ref> <turn_id>
│
├── brains                                       # unchanged
│   └── build
│       --agent-def-dir, --tool, --skill, --config-profile,
│       --cred-profile, --recipe, --runtime-root, --home-id,
│       --reuse-home, --launch-overrides, --agent-name, --agent-id
│
└── admin                                        # unchanged
    └── cleanup-registry  --grace-seconds

RETIRED (removed entirely):
  houmao-mgr cao *           → houmao-mgr agents launch / server sessions shutdown
  houmao-mgr launch          → houmao-mgr agents launch
  houmao-mgr cao flow *      → dropped (reintroduce under agents flow if needed)
```

### Command migration map

| Old command | New command |
|---|---|
| `houmao-mgr launch --agents X --provider Y` | `houmao-mgr agents launch --agents X --provider Y` |
| `houmao-mgr launch --headless --agents X` | `houmao-mgr agents launch --headless --agents X` |
| `houmao-mgr cao launch --agents X` | `houmao-mgr agents launch --agents X` |
| `houmao-mgr cao info` | `houmao-mgr server status` |
| `houmao-mgr cao shutdown --all` | `houmao-mgr server sessions shutdown --all` |
| `houmao-mgr cao shutdown --session S` | `houmao-mgr server sessions shutdown --session S` |
| `houmao-mgr cao init` | dropped |
| `houmao-mgr cao mcp-server` | dropped (already retired) |
| `houmao-mgr cao flow *` | dropped (reintroduce if needed) |
| `houmao-server serve` | `houmao-mgr server start` |

## Risks / Trade-offs

- **[Risk] Scripts using `houmao-mgr cao launch` break immediately** → Mitigation: Search repo for all `cao launch` references in scripts, tests, and docs; update them in the same change. The `cao` commands are internal.
- **[Risk] `agents launch` TUI mode may not perfectly replicate the server-mediated TUI experience** → Mitigation: The core difference is that the server tracks TUI state via its supervisor. Without the server, TUI state tracking doesn't happen automatically. Accept this as a known limitation — users who want TUI state tracking should start the server first and use server-backed features.
- **[Risk] Registry-first discovery fails for agents launched before this change** → Mitigation: Fall back to `--port` / default server URL when registry lookup fails. The discovery chain is: registry → `--port` flag → environment variable → default URL.
- **[Trade-off] `cao flow` functionality is dropped** → The flow subcommands (list/add/remove/enable/disable/run) managed local scheduled agent flows. This is niche functionality that can be reintroduced under `agents flow` or `admin flow` if needed.
