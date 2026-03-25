## Why

The `houmao-mgr` CLI has an unclear command shape: the `cao` group and top-level `launch` both launch agents through the server, the `agents` group has no `launch` command, server lifecycle lives in a separate binary, and invoking `houmao-mgr` without arguments throws a Python exception instead of printing help. Agent launching currently requires a running `houmao-server` even though the brain build → launch → registry-publish flow is inherently local. The CLI needs restructuring so that server lifecycle and agent lifecycle are cleanly separated command groups.

## What Changes

- **BREAKING**: Retire the `houmao-mgr cao` command group entirely (launch, info, init, mcp-server, shutdown, flow).
- **BREAKING**: Remove the top-level `houmao-mgr launch` command.
- Add `houmao-mgr server` group with subcommands for server lifecycle: `start`, `stop`, `status`, and `sessions` (list/show/shutdown).
- Add `houmao-mgr agents launch` command that performs brain building and agent launch locally without requiring `houmao-server` — follows the pipeline: select recipe → build brain → launch agent via `start_runtime_session()` → publish shared registry record.
- Make `houmao-mgr agents list` discover agents from the shared registry first, optionally enriching from a running server if one is available.
- Ensure `houmao-mgr` (no args) prints help instead of raising an exception.
- Agent post-launch operations (`agents prompt`, `agents stop`, etc.) discover the server URL via the shared registry record rather than requiring an explicit `--port` flag.

## Capabilities

### New Capabilities

- `houmao-mgr-server-group`: Server lifecycle commands (`start`, `stop`, `status`, `sessions list/show/shutdown`) under the `houmao-mgr server` namespace, absorbing the `houmao-server serve` entry point and the session management from `cao shutdown`.
- `houmao-mgr-agents-launch`: Local agent launch command under `houmao-mgr agents launch` that builds the brain and starts the agent without requiring `houmao-server`, using `start_runtime_session()` directly and publishing to the shared registry.
- `houmao-mgr-registry-discovery`: Registry-first agent and server discovery for `houmao-mgr agents` post-launch commands — looks up the agent in the shared registry to resolve backend type and server URL instead of requiring `--port`.

### Modified Capabilities

- `houmao-srv-ctrl-native-cli`: The root CLI group gains `invoke_without_command=True` to print help on bare invocation, `cao` group and top-level `launch` are removed, `server` group is added.
- `houmao-srv-ctrl-cao-compat`: The CAO compatibility namespace is retired; commands that were unique to it (flow management) are either moved to `agents` or dropped.

## Impact

- **CLI surface**: `houmao-mgr cao *` and `houmao-mgr launch` are removed. Users must switch to `houmao-mgr agents launch` and `houmao-mgr server *`.
- **Source files**: `src/houmao/srv_ctrl/commands/cao.py` retired. `src/houmao/srv_ctrl/commands/launch.py` retired or refactored into agents launch. New `src/houmao/srv_ctrl/commands/server.py` created. `src/houmao/srv_ctrl/commands/agents/core.py` extended with launch command. `src/houmao/srv_ctrl/commands/main.py` updated for new command tree.
- **Entry points**: `houmao-server` CLI entry point may remain for backward compat but `houmao-mgr server start` becomes the recommended way.
- **Shared registry**: No schema changes needed — the existing `LiveAgentRegistryRecordV2` already contains `backend`, `tool`, and `manifest_path` fields sufficient for discovery.
- **Tests**: Integration tests referencing `houmao-mgr cao launch` or `houmao-mgr launch` will need updating.
