## Why

`houmao-mgr agents gateway ...` currently exposes gateway lifecycle, queue-mediated prompt control, raw send-keys, and notifier control, but it does not expose the gateway-owned TUI tracking surface directly. Operators who want exact live parser and tracker state must fall back to `agents show`, direct HTTP calls, or ad hoc polling, which makes the raw gateway tracking workflow harder to discover and less coherent than the rest of the managed-agent gateway surface.

We also want gateway TUI history to stay lightweight and operationally useful rather than becoming another durable artifact store. A bounded in-memory snapshot buffer is sufficient for short-horizon debugging and watch-style inspection.

## What Changes

- Add a native `houmao-mgr agents gateway tui ...` subtree for raw gateway-owned TUI inspection and tracking functions.
- Add `tui state` as the one-shot gateway-owned tracked-state read surface for one managed agent.
- Add `tui history` as a bounded recent snapshot-history read surface backed by in-memory gateway tracking state.
- Add `tui watch` as a polling-oriented operator surface over gateway-owned tracked state.
- Add `tui note-prompt` as the explicit prompt-provenance helper under the gateway TUI subtree instead of leaving it available only as a raw HTTP route.
- Add pair-owned managed-agent gateway proxy routes for the TUI subtree so `houmao-mgr` does not need direct gateway host or port discovery when operating through `houmao-server` or `houmao-passive-server`.
- Keep gateway TUI history bounded to an internal Python-configured maximum of 1000 stored snapshots per tracked session. This limit is not exposed as a user-facing CLI or API tuning option in this change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-gateway`: expose gateway-owned TUI state, bounded snapshot history, and prompt-note tracking as a supported gateway operator surface.
- `official-tui-state-tracking`: retain a bounded in-memory snapshot history for live tracked TUI sessions so gateway-owned consumers can inspect recent tracked snapshots.
- `houmao-srv-ctrl-native-cli`: add `houmao-mgr agents gateway tui state|history|watch|note-prompt` with the same managed-agent selector and current-session targeting rules as the rest of `agents gateway`.
- `houmao-server-agent-api`: add managed-agent gateway TUI proxy routes so pair clients can read gateway-owned TUI state and history or record prompt notes without direct listener discovery.
- `passive-server-gateway-proxy`: add passive-server proxy support for the managed-agent gateway TUI routes.

## Impact

- Affected code:
  - `src/houmao/srv_ctrl/commands/agents/gateway.py`
  - `src/houmao/srv_ctrl/commands/managed_agents.py`
  - `src/houmao/agents/realm_controller/gateway_client.py`
  - `src/houmao/agents/realm_controller/gateway_service.py`
  - shared TUI tracking modules and models
  - `src/houmao/server/app.py`, `src/houmao/server/service.py`, `src/houmao/server/client.py`
  - `src/houmao/passive_server/app.py`, `src/houmao/passive_server/service.py`, `src/houmao/passive_server/client.py`
- Affected docs:
  - `docs/reference/cli.md`
  - gateway reference and managed-agent API reference pages
- Affected tests:
  - CLI command coverage for `agents gateway tui ...`
  - server and passive-server gateway proxy tests
  - gateway service and tracking retention tests
