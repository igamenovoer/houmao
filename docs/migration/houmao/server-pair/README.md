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

1. It exposes the CAO-compatible HTTP surface that current callers already expect.
2. It owns Houmao-specific state that CAO did not own before.

Implemented server scope includes:

- CAO-compatible HTTP route mapping for the supported upstream CAO surface
- a supervised child `cao-server` in the shallow v1 architecture
- derived child listener address `public_port + 1`
- Houmao-owned `GET /health` additive metadata
- Houmao-owned current-instance metadata
- one background worker per known tmux-backed tracked session
- direct tmux pane capture and process-based TUI up/down detection
- official live parsing through the shared parser stack
- explicit transport/process/parse state, derived operator state, stability metadata, and bounded in-memory recent transitions
- server-local delegated-launch registration records
- a Houmao-owned server root under `<runtime-root>/houmao_servers/<host>-<port>/`

### `houmao-srv-ctrl`

`houmao-srv-ctrl` is now a CAO-compatible service-management CLI that preserves the familiar command family while keeping Houmao in the authority path.

Implemented CLI scope includes:

- supported command family:
  - `flow`
  - `info`
  - `init`
  - `install`
  - `launch`
  - `mcp-server`
  - `shutdown`
- delegation of most commands to the installed `cao` executable
- supported-pair enforcement for commands that must target a real `houmao-server`
- `launch` follow-up registration back into `houmao-server`
- Houmao-owned runtime artifact materialization after successful delegated launch

### Runtime Integration

The runtime now supports a first-class persisted backend identity:

- `backend = "houmao_server_rest"`

That backend persists the public `houmao-server` transport identity instead of pretending the session is still owned directly by `cao_rest`.

Implemented runtime scope includes:

- dedicated `houmao_server` manifest sections
- runtime-owned session roots and manifests for delegated launches
- gateway and registry compatibility through those runtime-owned artifacts
- runtime control paths that route `houmao_server_rest` sessions through `houmao-server`

## What Stayed The Same

- `houmao-cli` remains the runtime and agent lifecycle CLI. It is not the CAO-compatible service-management wrapper.
- Direct CAO-based flows still exist while `houmao-server` adoption remains opt-in.
- `houmao-server` still uses a supervised child `cao-server` behind the public Houmao boundary for delegated control routes.
- The watch plane is no longer child-CAO-shaped even though the control plane still delegates in v1.

## Recommended Reading Order

1. [What We Tested](tested.md)
2. [Migration Guide](migration-guide.md)
3. [Houmao Server Pair Reference](../../../reference/houmao_server_pair.md)
4. [Houmao Server Filesystem Reference](../../../reference/system-files/houmao-server.md)
