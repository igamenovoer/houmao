# Houmao Server Pair Migration Pack

This migration pack describes the supported Houmao-managed replacement pair:

- `houmao-server`
- `houmao-mgr`

Together, those tools replace the supported operator path that used to be expressed as:

- `cao-server`
- `cao`

Mixed pairs such as `houmao-server + cao` or `cao-server + houmao-mgr` are unsupported.

## What We Implemented

### `houmao-server`

`houmao-server` is now the public HTTP authority for the pair and owns the CAO-compatible control slice directly.

Implemented server scope includes:

- native Houmao-owned CAO-compatible control core behind `/cao/*`
- server-local dispatch for the preserved `/cao/*` route family instead of reverse proxying to a supervised child `cao-server`
- preserved root `GET /health` compatibility identity with `service="cli-agent-orchestrator"` plus `houmao_service="houmao-server"`, without `child_cao` metadata
- Houmao-owned current-instance metadata under `/houmao/server/current-instance`
- launch-time native selector resolution and compatibility projection for session-backed startup
- Houmao-owned compatibility registry persistence for CAO-shaped sessions, terminals, and inbox messages
- shared managed-agent routes under `/houmao/agents/*`
- native headless lifecycle routes for launch, stop, turns, events, artifacts, and best-effort interrupt
- direct tmux/process watch, official parser integration, and Houmao-owned tracked terminal state
- server-owned managed-agent authority records under `state/managed_agents/<tracked_agent_id>/`

### `houmao-mgr`

`houmao-mgr` remains the pair-management CLI, but the supported command tree is now simplified and Houmao-owned end to end.

Implemented CLI scope includes:

- `server start|stop|status|sessions ...` for server lifecycle and server-owned session management
- `agents launch|list|show|state|history|prompt|interrupt|stop` for managed-agent lifecycle
- `agents gateway ...`, `agents mail ...`, and `agents turn ...` for follow-up workflows
- local `brains build` and `admin cleanup-registry` wrappers for non-server authority
- direct local `agents launch` for Codex, Claude Code, and Gemini CLI providers without requiring `houmao-server`

The explicit `houmao-mgr cao ...` namespace and top-level `houmao-mgr launch` are retired from the supported surface.

### Runtime Integration

Runtime-backed terminal sessions launched through the pair continue to persist:

- `backend = "houmao_server_rest"`

That preserves the existing pair runtime seam while redirecting the underlying CAO-compatible authority to `houmao-server` itself.

## What Changed

- `houmao-server` no longer supervises a child `cao-server` for the supported pair path.
- `houmao-mgr` no longer depends on the explicit `cao` compatibility namespace for the supported command family.
- pair startup no longer includes public compatibility-profile install commands.
- standalone `houmao-cao-server` is retired and fails fast with migration guidance.
- standalone `houmao-cli` workflows that would create or control raw `backend="cao_rest"` sessions are retired and fail fast with migration guidance.

## What Stayed The Same

- `houmao-cli` remains the runtime and agent lifecycle CLI.
- the public pair boundary remains `houmao-server + houmao-mgr`.
- the explicit `/cao/*` HTTP namespace remains present for compatibility, but CLI guidance now points to `houmao-mgr server ...` and `houmao-mgr agents ...`.
- pair-managed runtime artifacts, gateway attachability publication, and reserved tmux window `0` behavior remain centered on `houmao_server_rest`.

## Recommended Reading Order

1. [What We Tested](tested.md)
2. [Migration Guide](migration-guide.md)
3. [Houmao Server Pair Reference](../../../reference/houmao_server_pair.md)
4. [Houmao Server Filesystem Reference](../../../reference/system-files/houmao-server.md)
5. [TUI Handling Internals](../../../developer/houmao-server/internals/README.md)
