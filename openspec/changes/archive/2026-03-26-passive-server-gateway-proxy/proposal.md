## Why

The passive server can discover and list agents (Step 2 complete) but cannot interact with their gateways. Six of the target API endpoints are pure forwards to agent gateways — gateway status, prompt submission, and mail operations. These are the simplest endpoints to add because the passive server acts as a thin proxy: resolve the agent, read gateway coordinates from the registry record, create a `GatewayClient`, and forward the request/response. This unlocks remote prompt delivery and mail interaction through the passive server without any direct tmux involvement.

## What Changes

- Add gateway proxy logic to the passive server: resolve an agent's gateway coordinates from the discovery index, instantiate a `GatewayClient`, and forward HTTP requests.
- Add six gateway proxy endpoints:
  - `GET /houmao/agents/{agent_ref}/gateway` — forward to gateway `GET /v1/status`.
  - `POST /houmao/agents/{agent_ref}/gateway/requests` — forward to gateway `POST /v1/requests`.
  - `GET /houmao/agents/{agent_ref}/mail/status` — forward to gateway `GET /v1/mail/status`.
  - `POST /houmao/agents/{agent_ref}/mail/check` — forward to gateway `POST /v1/mail/check`.
  - `POST /houmao/agents/{agent_ref}/mail/send` — forward to gateway `POST /v1/mail/send`.
  - `POST /houmao/agents/{agent_ref}/mail/reply` — forward to gateway `POST /v1/mail/reply`.
- Return 404 when the agent is not found, 409 when the agent name is ambiguous, and 502 when the gateway is not attached or unreachable.

## Capabilities

### New Capabilities
- `passive-server-gateway-proxy`: Covers gateway proxy resolution (registry record → `GatewayClient`) and all six forwarding endpoints with error handling for missing agents and unreachable gateways.

### Modified Capabilities
<!-- No spec-level requirement changes to existing capabilities. The passive server reuses
     the existing GatewayClient and gateway models as a consumer. The passive-server-agent-discovery
     spec is unchanged — discovery still works the same way, and the proxy reads from the same index. -->

## Impact

- **New code in `src/houmao/passive_server/`**: gateway proxy logic (service methods or a thin proxy module), new route handlers in `app.py`.
- **Dependencies on existing code**: `houmao.agents.realm_controller.gateway_client.GatewayClient`, `houmao.agents.realm_controller.gateway_models` (all request/response model classes), `houmao.agents.realm_controller.gateway_client.GatewayEndpoint`.
- **New tests in `tests/unit/passive_server/`**: gateway proxy service tests and HTTP contract tests.
- **No changes to existing server, gateway, registry, or discovery code.** The passive server is a new consumer of the existing `GatewayClient` API.
