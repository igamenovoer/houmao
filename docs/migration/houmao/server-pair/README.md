# Houmao Server Pair Migration Pack

This migration pack introduces the newly implemented Houmao-managed replacement pair:

- `houmao-server`
- `houmao-srv-ctrl`

Together, those tools are the supported Houmao replacement for:

- `cao-server`
- `cao`

This pack is intentionally about the pair, not about isolated cross-product combinations. Mixed pairs such as `houmao-server + cao` or `cao-server + houmao-srv-ctrl` are unsupported in this implementation.

## What We Implemented

### `houmao-server`

`houmao-server` is now a first-party HTTP service with two responsibilities:

1. It exposes the CAO-compatible HTTP surface under an explicit `/cao/*` namespace.
2. It owns Houmao-specific state that CAO did not own before.

Implemented server scope includes:

- CAO-compatible `/cao/*` HTTP route mapping for the supported upstream CAO surface
- a supervised child `cao-server` in the shallow v1 architecture
- derived child listener address `public_port + 1`
- Houmao-owned `GET /health` additive metadata
- Houmao-owned current-instance metadata
- shared managed-agent routes under `/houmao/agents/*` for transport-neutral discovery, coarse state, and bounded history
- native headless lifecycle routes for launch, stop, turns, events, artifacts, and interrupt
- one background worker per known tmux-backed tracked session
- direct tmux pane capture and process-based TUI up/down detection
- official live parsing through the shared parser stack
- explicit transport/process/parse diagnostics, simplified `diagnostics` / `surface` / `turn` / `last_turn` tracked state, generic stability metadata, and bounded in-memory recent transitions
- server-local delegated-launch registration records
- server-owned native headless authority records under `state/managed_agents/<tracked_agent_id>/`
- a Houmao-owned server root under `<runtime-root>/houmao_servers/<host>-<port>/`

### `houmao-srv-ctrl`

`houmao-srv-ctrl` is now a pair service-management CLI with an explicit CAO-compatible namespace.

Implemented CLI scope includes:

- top-level Houmao-owned pair commands:
  - `install`
  - `launch`
- explicit CAO-compatible namespace under `houmao-srv-ctrl cao`:
  - `flow`
  - `info`
  - `init`
  - `install`
  - `launch`
  - `mcp-server`
  - `shutdown`
- local-only delegation of `cao flow`, `cao init`, `cao install`, and `cao mcp-server` to the installed `cao` executable
- pair-aware `cao launch`, `cao info`, and `cao shutdown` wrappers over the supported `houmao-server` boundary
- terminal-backed launch follow-up registration back into `houmao-server`
- native top-level `launch --headless` translation into the Houmao headless launch API
- Houmao-owned runtime artifact materialization after successful terminal-backed launch

### Runtime Integration

The runtime now supports a first-class persisted backend identity:

- `backend = "houmao_server_rest"`

That backend persists the public `houmao-server` transport identity instead of pretending the session is still owned directly by `cao_rest`.

Implemented runtime scope includes:

- dedicated `houmao_server` manifest sections
- runtime-owned session roots and manifests for delegated launches
- gateway and registry compatibility through those runtime-owned artifacts
- runtime control paths that route `houmao_server_rest` sessions through `houmao-server`
- native headless runtime sessions that remain on their headless backend while exposing server-owned control through `/houmao/agents/*`

## What Stayed The Same

- `houmao-cli` remains the runtime and agent lifecycle CLI. It is not the CAO-compatible service-management wrapper.
- Direct CAO-based flows still exist while `houmao-server` adoption remains opt-in.
- `houmao-server` still uses a supervised child `cao-server` behind the public Houmao boundary for delegated control routes.
- The watch plane is no longer child-CAO-shaped even though the control plane still delegates in v1.

## Recommended Reading Order

1. [What We Tested](tested.md)
2. [Migration Guide](migration-guide.md)
3. [TUI Handling Internals](../../../developer/houmao-server/internals/README.md)
4. [Houmao Server Pair Reference](../../../reference/houmao_server_pair.md)
5. [Houmao Server Filesystem Reference](../../../reference/system-files/houmao-server.md)
