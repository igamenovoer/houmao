## Why

The AG-UI workbench tmux tab currently depends on `node-pty`, but the supported development command runs the server under Bun. In this workspace, `node-pty` child PTYs exit immediately under Bun while the same tmux attachment works under Node, causing every browser tmux tab to show `[tmux] attachment ended`.

## What Changes

- Add a runtime-selected PTY backend boundary for the workbench server tmux bridge.
- Keep the existing `node-pty` implementation for Node-backed workbench server runs.
- Add a Bun-backed implementation using Bun's first-party `Bun.Terminal` API when the server runs under Bun with PTY support available.
- Preserve the existing private browser tmux WebSocket protocol, including attach, input, resize, close, output, attached, error, and exit messages.
- Improve diagnostics so unsupported or failed PTY backend selection reports a deterministic error instead of a generic attachment-ended message.
- Update workbench documentation and tests to cover Node and Bun runtime behavior without requiring the GUI to run under only one JavaScript runtime.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `ag-ui-workbench-local-server`: The server-owned tmux bridge must select a functional PTY backend for the active JavaScript runtime and expose deterministic diagnostics when no backend can attach.

## Impact

- Affected code: `apps/ag-ui-workbench/src/server/tmuxBridge.ts`, likely a new server-side PTY adapter module, and tmux bridge tests.
- Affected docs: `apps/ag-ui-workbench/README.md` and the existing hint guide under `context/hints/`.
- Dependencies: no new dependency is required for Bun 1.3.5+ because `Bun.Terminal` is built in; `node-pty` remains required for Node runs.
- Systems: local single-user AG-UI workbench server and browser tmux tabs.
