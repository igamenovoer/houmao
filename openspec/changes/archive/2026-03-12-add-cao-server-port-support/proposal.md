## Why

The tracked CAO fork now supports explicit server-port selection, but this repo still models CAO launcher support as fixed to `localhost:9889` and `127.0.0.1:9889`. That mismatch blocks launcher-managed multi-port workflows, keeps a stale fixed-port issue note alive, and forces our loopback transport policy to stay narrower than the CAO server we now ship against.

## What Changes

- Expand CAO launcher config validation from an exact `:9889` allowlist to loopback `http://localhost:<port>` and `http://127.0.0.1:<port>` URLs with explicit ports.
- Preserve and explicitly require launcher CLI arguments that can override config-file values on demand for one invocation, including non-default `base_url` values used to select a different loopback port.
- Teach launcher-managed `start` to derive the requested port from `base_url` and launch `cao-server` with that port so `status`, `start`, `stop`, and runtime artifacts stay aligned to one base URL.
- Update loopback no-proxy classification so launcher probes, the CAO REST client, and runtime-managed tmux env injection apply the existing loopback bypass policy to supported loopback CAO URLs on any explicit port rather than only `:9889`.
- Update repo-owned non-interactive CAO demos and exploratory helpers that currently treat local CAO as exactly `:9889` so they accept supported loopback ports while preserving intentionally fixed tutorial/demo contracts.
- Refresh launcher docs, examples, tests, and issue notes to describe configurable loopback port support in the tracked CAO fork.
- Keep the interactive CAO demo's fixed-loopback `127.0.0.1:9889` contract unchanged in this change.
- Keep the CAO launcher tutorial/demo pack pinned to `127.0.0.1:9889` in this change for reproducibility.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cao-server-launcher`: launcher config, validation, startup, and lifecycle management now support configurable loopback CAO ports instead of only `:9889`
- `cao-rest-client-contract`: loopback CAO proxy-bypass behavior now applies to supported loopback CAO base URLs with any explicit port
- `brain-launch-runtime`: runtime-owned loopback CAO transport policy and tmux env injection now follow the broader loopback-with-port contract
- `cao-loopback-no-proxy`: supported loopback CAO scope expands from two exact URLs to loopback hosts with explicit ports
- `cao-claude-demo-scripts`: local-only CAO demo packs accept supported loopback CAO base URLs with explicit ports instead of exact `:9889` values

## Impact

- Affected code: `src/gig_agents/cao/`, `src/gig_agents/agents/brain_launch_runtime/backends/cao_rest.py`, repo-owned non-interactive CAO demo scripts, exploratory helpers, launcher/demo docs, and CAO launcher tests
- External dependency behavior: launcher startup now relies on the tracked CAO fork honoring an explicit port setting when `cao-server` starts
- Operational impact: developers can run launcher-managed CAO services on non-default loopback ports without changing artifact ownership semantics
- Out of scope: the interactive demo and the CAO launcher tutorial/demo pack remain pinned to `http://127.0.0.1:9889`
