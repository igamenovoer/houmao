## Why

The passive server now has enough lifecycle and Step 5 route surface to be exercised as a real pair authority, but the typed client layer and `houmao-mgr` still assume a `houmao-server`-only world. We need a Step 6 compatibility change now so the passive server can actually be targeted by pair commands, gateway-managed headless callbacks, and parallel validation workflows.

## What Changes

- Add a passive-server-aware client layer that can detect the server flavor from `GET /health`, call the passive lifecycle endpoints, and expose the managed-agent routes needed by `houmao-mgr` and other pair consumers.
- Update `houmao-mgr` server and managed-agent commands to treat `houmao-passive-server` as a supported pair authority instead of rejecting anything that is not `houmao-server`.
- Define how pair-facing code adapts response models between the old server and the passive server so command logic can stay registry-first and transport-agnostic.
- Update gateway-managed headless control paths that currently instantiate `HoumaoServerClient` directly so they can talk to passive-server-managed headless agents through the same managed API base URL metadata.
- Add compatibility tests and operator guidance for using the passive server during Step 7 parallel validation.

## Capabilities

### New Capabilities
- `passive-server-client-compatibility`: A typed client and compatibility layer for targeting `houmao-passive-server` as a pair authority, including lifecycle, managed-agent inspection/control, and gateway-managed headless callbacks.

### Modified Capabilities
- `houmao-srv-ctrl-native-cli`: `houmao-mgr` server and server-backed managed-agent commands now accept `houmao-passive-server` as a supported pair authority and route through the passive-server-aware client path when appropriate.

## Impact

- **Code**: `src/houmao/server/client.py` or a new passive-server client module, `src/houmao/srv_ctrl/commands/common.py`, `src/houmao/srv_ctrl/commands/server.py`, `src/houmao/srv_ctrl/commands/managed_agents.py`, and `src/houmao/agents/realm_controller/gateway_service.py`.
- **APIs**: No new passive-server endpoints are required, but the typed client contract and pair-command expectations change to support both `houmao-server` and `houmao-passive-server`.
- **Operators**: `houmao-mgr` can target a passive server on its own port during Step 7 side-by-side validation without being mistaken for an unsupported raw CAO server.
- **Validation**: New tests will be needed for health detection, lifecycle commands, managed-agent commands, and gateway-managed headless control against the passive server.
