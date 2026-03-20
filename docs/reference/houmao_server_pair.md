# Houmao Server Pair

`houmao-server` and `houmao-srv-ctrl` are the supported Houmao-managed replacement pair for `cao-server` and `cao`.

The intent of this pair is narrow and explicit:

- `houmao-server` is the public HTTP authority.
- `houmao-srv-ctrl` is the CAO-compatible CLI wrapper that delegates to the installed `cao` executable and registers successful launches back into `houmao-server`.
- Mixed pairs such as `houmao-server + cao` or `cao-server + houmao-srv-ctrl` are unsupported in this change.

For the maintained deep explanation of the live state tracker, turn anchors, lifecycle authority, and state transition rules behind `GET /houmao/terminals/{terminal_id}/state`, see the [Houmao Server Developer Guide](../developer/houmao-server/index.md).

## Compatibility Source Of Truth

Compatibility for this change is pinned to one exact upstream CAO source:

- Repository: `https://github.com/imsight-forks/cli-agent-orchestrator.git`
- Commit: `0fb3e5196570586593736a21262996ca622f53b6`
- Tracked local checkout: `extern/tracked/cli-agent-orchestrator`

That exact commit is the parity oracle for the CAO-compatible HTTP and CLI behavior implemented here. Houmao does not treat a floating branch name or whatever `cao-server` happens to be installed on `PATH` as the compatibility definition.

## Commands

Primary entrypoints for the paired replacement:

- `houmao-server`: serves the Houmao-owned CAO-compatible HTTP surface and Houmao extension routes
- `houmao-srv-ctrl`: exposes the supported CAO-compatible command family and delegates most commands to installed `cao`
- `houmao-cli`: remains the runtime/agent lifecycle CLI and stays outside the CAO-compatible service-management surface

Representative usage:

```bash
houmao-server serve --api-base-url http://127.0.0.1:9889
houmao-srv-ctrl install projection-demo --provider codex --port 9889
houmao-srv-ctrl info --port 9889
houmao-srv-ctrl launch --port 9889 --agents gpu-kernel-coder --provider codex
```

## Architecture

The pair still uses a supervised child `cao-server` for CAO-compatible control routes, but live TUI tracking no longer goes through that child. `houmao-server` now owns the watch plane directly:

- direct tmux pane resolution and capture
- live process-tree inspection to determine whether the supported TUI is up or down
- official parser selection through the shared parser stack
- continuous in-memory live state and bounded recent transitions

The public contract stays Houmao-owned:

- callers talk to `houmao-server`
- runtime-owned `houmao_server_rest` sessions persist the public Houmao server base URL and terminal identity
- child CAO details stay behind the public contract for the delegated control plane
- terminal-keyed Houmao extension routes resolve through Houmao-owned tracked-session identity instead of making `terminal_id` the internal watch authority

The child listener address is derived mechanically as `public_port + 1` and stays loopback-only. There is no separate user-facing child-port override in this design.

Pair-targeted profile installation follows the same boundary:

- `houmao-srv-ctrl install --port <public-port> ...` identifies one public `houmao-server`
- `houmao-server` resolves the child-managed CAO home internally
- callers do not compute or mutate hidden `child_cao` filesystem paths directly

## Persistence Boundary

The v1 boundary is intentionally split into three groups.

Filesystem-authoritative artifacts:

- runtime-owned session roots and manifests
- shared-registry `live_agents/<agent-id>/record.json` pointers while the registry bridge remains in use
- delegated `houmao-srv-ctrl launch` manifests and session roots written under the normal runtime-owned `sessions/houmao_server_rest/...` layout

Filesystem-backed compatibility, debug, or migration views:

- `houmao-server` current-instance and pid files
- child launcher config, pid, ownership, and runtime artifacts under the internal child root
- delegated-launch `sessions/<session>/registration.json` under the server root

Memory-primary live control-plane state:

- known-session registry entries rebuilt from registration records and verified against live tmux
- active watch-worker ownership
- explicit transport/process/parse state for tracked sessions
- latest parsed supported-TUI surface, derived operator state, stability metadata, and bounded recent transitions

Live terminal state is now authoritative in server memory. `houmao-server` no longer writes per-terminal `current.json`, `samples.ndjson`, or `transitions.ndjson` files for the tracker contract.

## `houmao_server_rest` Runtime Identity

Runtime-owned sessions that use the server-backed mode persist `backend = "houmao_server_rest"`.

That backend uses dedicated persisted sections instead of overloading the older `cao_rest` contract:

- session manifests write a `houmao_server` section with `api_base_url`, `session_name`, `terminal_id`, `parsing_mode`, optional `tmux_window_name`, and `turn_index`
- gateway attach contracts use Houmao-specific backend metadata
- shared-registry records still point back to the runtime-owned manifest and session root instead of copying runtime state into the registry

This keeps child CAO adapter details out of the runtime-owned public contract while preserving existing discovery and gateway flows during the transition.

## Hidden Child Storage Model

`houmao-server` provisions the child CAO support state under a Houmao-owned per-server root instead of introducing a user-facing CAO home contract for the pair.

For one public base URL, the server-owned tree lives under:

```text
<runtime-root>/houmao_servers/<host>-<port>/
```

The child-specific subtree is:

```text
<server-root>/child_cao/
  launcher.toml
  runtime/
```

This subtree is internal Houmao-managed support state. Operators may inspect it for debugging, but it is not the public control surface.

That includes agent-profile installation. The supported pair-owned path is:

```bash
houmao-srv-ctrl install <agent-source> --provider <provider> --port <public-port>
```

The install request is routed through `houmao-server`, which performs the child-CAO mutation inside the managed support subtree without promoting that subtree into a caller-facing contract.

## Transitional Registry Bridge

Delegated `houmao-srv-ctrl launch` flows still publish shared-registry pointers in v1 when the current runtime/gateway flows require those pointers.

Those registry records remain pointer-oriented:

- they reference the Houmao-owned manifest and session root
- they do not become a second copy of runtime state
- they remain a compatibility bridge while future discovery moves toward server-owned query surfaces

## Migration Direction

This pair is a migration strategy, not the final architecture.

The public names and persisted backend identity are already Houmao-owned so that future native Houmao terminal backends can replace the child CAO adapter without forcing another public rename or persisted-contract reset.

## Source References

- [`src/houmao/server/app.py`](../../src/houmao/server/app.py)
- [`src/houmao/server/service.py`](../../src/houmao/server/service.py)
- [`src/houmao/server/child_cao.py`](../../src/houmao/server/child_cao.py)
- [`src/houmao/server/models.py`](../../src/houmao/server/models.py)
- [`src/houmao/srv_ctrl/commands/launch.py`](../../src/houmao/srv_ctrl/commands/launch.py)
- [`src/houmao/srv_ctrl/commands/runtime_artifacts.py`](../../src/houmao/srv_ctrl/commands/runtime_artifacts.py)
- [`src/houmao/agents/realm_controller/manifest.py`](../../src/houmao/agents/realm_controller/manifest.py)
- [`src/houmao/agents/realm_controller/runtime.py`](../../src/houmao/agents/realm_controller/runtime.py)
- [`src/houmao/cao/pinned.py`](../../src/houmao/cao/pinned.py)
