## Why

Gateway attach and gateway-mediated operations use loopback HTTP calls to a local per-agent gateway listener. Ambient proxy variables can route those loopback calls through a proxy, causing attach readiness to time out even after the gateway process has started.

Operators also need an explicit escape hatch for traffic-capture or debugging setups where they intentionally want gateway HTTP calls to honor proxy environment settings.

## What Changes

- Define gateway client proxy policy: direct loopback communication is the default for all live gateway HTTP calls.
- Add an explicit environment override, `HOUMAO_GATEWAY_RESPECT_PROXY_ENV=1`, that makes gateway client HTTP calls use the caller's proxy environment.
- Require gateway attach readiness errors to keep useful diagnostics when health probes fail repeatedly.
- Add regression coverage for proxy-contaminated environments and preserve existing gateway attach behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-gateway`: define live gateway HTTP client proxy bypass behavior and the opt-in environment override for respecting proxy settings.

## Impact

- Affected code: `src/houmao/agents/realm_controller/gateway_client.py`, `src/houmao/agents/realm_controller/runtime.py`, gateway-related CLI/server proxy paths that instantiate `GatewayClient`.
- Affected tests: gateway client unit coverage, gateway attach readiness/unit coverage, and existing unit suite.
- No external dependency changes.
- No breaking CLI or HTTP API change; proxy use becomes explicit for gateway client calls.
