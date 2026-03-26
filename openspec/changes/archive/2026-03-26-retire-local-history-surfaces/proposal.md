## Why

The local/serverless history surfaces are not pulling their weight. `houmao-mgr agents history` is a thin wrapper over mixed local tracker state and persisted headless artifacts, and for local TUI sessions it can present non-authoritative or misleading output compared with the supported `state` and `show` views. At the same time, runtime-owned local gateway workflows no longer need `/v1/control/tui/history` to validate prompt submission or current TUI posture.

We still have one important constraint: the integrated CAO/server module consumes gateway and managed-agent history contracts today. This change therefore needs a scoped retirement that removes local/serverless history surfaces without modifying the integrated server/CAO path.

## What Changes

- **BREAKING** Remove `houmao-mgr agents history` from the supported native CLI surface.
- Retire local/serverless workflow reliance on gateway TUI history for runtime-owned `local_interactive` sessions; local tracking remains centered on `GET /v1/control/tui/state` plus explicit prompt-note evidence.
- Keep shared history plumbing that is still required by the integrated CAO/server module, but treat it as compatibility-only outside this change rather than a supported local/serverless operator surface.
- Update repo-owned docs, tests, and workflow notes so local inspection uses supported surfaces such as `houmao-mgr agents state`, `houmao-mgr agents show`, gateway TUI state, and managed headless turn inspection instead of generic local history endpoints.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-srv-ctrl-native-cli`: retire `houmao-mgr agents history` and remove native CLI guidance that treats managed-agent history as a supported local inspection surface.
- `agent-gateway`: narrow the runtime-owned `local_interactive` tracking contract so local/serverless workflows rely on gateway-owned current state and explicit prompt-note evidence rather than gateway-owned history as a supported surface.

## Impact

- Affected code: `src/houmao/srv_ctrl/commands/agents/core.py`, `src/houmao/srv_ctrl/commands/managed_agents.py`, and local gateway/runtime-owned tracking tests and workflow notes.
- Operator surface: `houmao-mgr agents --help`, local/serverless inspection guidance, and runtime-owned gateway TUI tracking expectations.
- Compatibility boundary: gateway/shared-tracker history plumbing that is still consumed by the integrated server path may remain in place in this change.
- Explicit non-goal: no modifications under `src/houmao/server/**` or other integrated CAO/server-owned modules in this change.
