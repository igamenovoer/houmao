# Serverless `houmao-mgr` Run Log: Foreground Gateway Drops Before Prompt On `james`

## Date
2026-03-26 10:55:05 UTC

## Status
Issue observed

## Scenario
Attach a foreground gateway to the serverless interactive Claude agent `james`, then send a prompt through the explicit gateway path while tracking gateway/TUI state.

## Attach Command
```bash
AGENTSYS_AGENT_DEF_DIR="$PWD/tests/fixtures/agents" \
pixi run houmao-mgr agents gateway attach \
  --foreground \
  --agent-name james
```

## Attach Result
The attach command reported a healthy foreground gateway:

```json
{
  "execution_mode": "tmux_auxiliary_window",
  "gateway_health": "healthy",
  "gateway_host": "127.0.0.1",
  "gateway_port": 38445,
  "gateway_tmux_window_index": "1",
  "managed_agent_connectivity": "connected",
  "request_admission": "open",
  "tmux_session_name": "james"
}
```

Immediately after attach, `tmux list-windows -t james` showed:

```text
0: agent
1: gateway
```

## Gateway Prompt Command
```bash
AGENTSYS_AGENT_DEF_DIR="$PWD/tests/fixtures/agents" \
pixi run houmao-mgr agents gateway prompt \
  --agent-name james \
  --prompt 'Reply with exactly GATEWAY_OK and nothing else.'
```

## Observed Failure
The explicit gateway prompt failed with:

```text
houmao.agents.realm_controller.errors.GatewayNoLiveInstanceError:
No live gateway is attached for session `james`.
```

## Tracking Observations

### Gateway-owned TUI tracker before prompt
Before the prompt attempt, `GET /v1/control/tui/state` on the reported gateway port showed the TUI was parsed, stable, and ready on the previous `JAMES_OK` completion:

- `diagnostics.availability: "available"`
- `surface.ready_posture: "yes"`
- `turn.phase: "ready"`
- tracked session `agent_name: "james"`
- `tmux_session_name: "james"`

### Post-failure gateway state
After the failed prompt:

- `tmux list-windows -t james` no longer showed the `gateway` window
- `houmao-mgr agents gateway status --agent-name james` returned:
  - `gateway_health: "not_attached"`
  - `gateway_port: null`
  - `request_admission: "blocked_unavailable"`

## Impact
Foreground gateway attach for the serverless local interactive agent appears to report a healthy live gateway, but the gateway instance disappears before an immediate explicit gateway prompt can be admitted.

This blocks the intended gateway-mediated prompt path and makes the initial attach-success payload unreliable for operators and tests.

## Notes
- This behavior reproduced twice in the same session.
- No `houmao-server` was involved.
- The target agent was addressed using the raw creation-time name `james`.
