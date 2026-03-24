# Houmao Server Pair Migration Pack

This migration pack describes the supported Houmao-managed replacement pair:

- `houmao-server`
- `houmao-srv-ctrl`

Together, those tools replace the supported operator path that used to be expressed as:

- `cao-server`
- `cao`

Mixed pairs such as `houmao-server + cao` or `cao-server + houmao-srv-ctrl` are unsupported.

## What We Implemented

### `houmao-server`

`houmao-server` is now the public HTTP authority for the pair and owns the CAO-compatible control slice directly.

Implemented server scope includes:

- native Houmao-owned CAO-compatible control core behind `/cao/*`
- server-local dispatch for the preserved `/cao/*` route family instead of reverse proxying to a supervised child `cao-server`
- preserved root `GET /health` compatibility identity with `service="cli-agent-orchestrator"` plus `houmao_service="houmao-server"`, without `child_cao` metadata
- Houmao-owned current-instance metadata under `/houmao/server/current-instance`
- Houmao-owned compatibility profile store and profile index under the server root
- Houmao-owned compatibility registry persistence for CAO-shaped sessions, terminals, and inbox messages
- shared managed-agent routes under `/houmao/agents/*`
- native headless lifecycle routes for launch, stop, turns, events, artifacts, and best-effort interrupt
- direct tmux/process watch, official parser integration, and Houmao-owned tracked terminal state
- server-owned managed-agent authority records under `state/managed_agents/<tracked_agent_id>/`

### `houmao-srv-ctrl`

`houmao-srv-ctrl` remains the pair service-management CLI and keeps the explicit `cao` namespace, but the implementation is now Houmao-owned.

Implemented CLI scope includes:

- top-level pair commands:
  - `install`
  - `launch`
  - `agents`
  - `brains`
  - `admin`
- explicit CAO-compatible namespace under `houmao-srv-ctrl cao`:
  - `flow`
  - `info`
  - `init`
  - `install`
  - `launch`
  - `mcp-server`
  - `shutdown`
- pair-routed `cao launch`, `cao info`, `cao shutdown`, and `cao install`
- local Houmao-owned compatibility helpers for `cao flow` and `cao init`
- explicit retirement guidance for `cao mcp-server` instead of passthrough to standalone CAO
- explicit launch provider coverage for `kiro_cli`, `claude_code`, `codex`, `gemini_cli`, `kimi_cli`, and `q_cli`
- terminal-backed launch follow-up registration back into `houmao-server`
- native top-level `launch --headless` translation into the Houmao headless launch API
- `agents gateway attach` current-session and explicit-target flows
- `agents prompt`, `agents mail ...`, and `agents turn ...` for covered pair-native follow-up workflows
- local `brains build` and `admin cleanup-registry` wrappers for non-server authority

### Runtime Integration

Runtime-backed terminal sessions launched through the pair continue to persist:

- `backend = "houmao_server_rest"`

That preserves the existing pair runtime seam while redirecting the underlying CAO-compatible authority to `houmao-server` itself.

## What Changed

- `houmao-server` no longer supervises a child `cao-server` for the supported pair path.
- `houmao-srv-ctrl cao ...` no longer depends on an installed `cao` executable for the supported command family.
- pair-targeted install now writes to a Houmao-managed compatibility profile store under the selected server root.
- standalone `houmao-cao-server` is retired and fails fast with migration guidance.
- standalone `houmao-cli` workflows that would create or control raw `backend="cao_rest"` sessions are retired and fail fast with migration guidance.

## What Stayed The Same

- `houmao-cli` remains the runtime and agent lifecycle CLI.
- the public pair boundary remains `houmao-server + houmao-srv-ctrl`.
- the explicit `/cao/*` HTTP namespace and `houmao-srv-ctrl cao ...` CLI namespace remain present for compatibility.
- pair-managed runtime artifacts, gateway attachability publication, and reserved tmux window `0` behavior remain centered on `houmao_server_rest`.

## Recommended Reading Order

1. [What We Tested](tested.md)
2. [Migration Guide](migration-guide.md)
3. [Houmao Server Pair Reference](../../../reference/houmao_server_pair.md)
4. [Houmao Server Filesystem Reference](../../../reference/system-files/houmao-server.md)
5. [TUI Handling Internals](../../../developer/houmao-server/internals/README.md)
