## Why

The AG-UI workbench now depends on `houmao-passive-server` discovery to list available agents, but the passive server has not had a recent functional manual validation path. We need repeatable operator-run scripts that exercise the real CLI process, HTTP surface, shared registry discovery, and gateway proxy behavior before relying on it for GUI testing.

## What Changes

- Add three manual passive-server validation scripts under `tests/manual/`.
- Cover server lifecycle and health using a real `houmao-passive-server serve` subprocess on a free local port.
- Cover registry discovery using isolated runtime and registry roots, a real tmux session, fresh and stale registry records, and HTTP list/resolve assertions.
- Cover gateway proxy behavior using a fake local gateway plus a registry-backed discovered agent with live gateway coordinates.
- Keep the scripts deterministic and cleanup-safe, with no real LLM turns required by default.

## Capabilities

### New Capabilities
- `passive-server-manual-validation`: Manual validation scripts for passive-server lifecycle, discovery, and gateway proxy behavior.

### Modified Capabilities

## Impact

- Adds files under `tests/manual/`.
- Uses existing passive-server CLI, registry models/storage helpers, tmux, and local HTTP clients.
- Does not change packaged runtime code, public APIs, dependencies, or Python package contents.
