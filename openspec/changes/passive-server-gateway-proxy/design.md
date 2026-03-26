## Context

The passive server has registry-driven agent discovery (Step 2) implemented. Each discovered agent's registry record includes a `gateway` field (`RegistryGatewayV1`) that contains `host` and `port` when a live gateway is attached. The existing `GatewayClient` class provides typed methods for all gateway HTTP operations (`status()`, `create_request()`, `mail_status()`, `check_mail()`, `send_mail()`, `reply_mail()`). The passive server needs to expose these gateway operations through its own HTTP endpoints by resolving agents from the discovery index and forwarding requests to the appropriate gateway.

The existing `houmao-server` already does this — it reads gateway coordinates from the session root's `state.json` file, creates a `GatewayClient`, and forwards. The passive server does the same but reads coordinates from the registry record's `gateway` field instead (which is populated from the same underlying data).

## Goals / Non-Goals

**Goals:**
- Add six gateway proxy endpoints to the passive server that forward to the agent's live gateway.
- Reuse the existing `GatewayClient` and gateway model classes without modification.
- Provide clear error responses when the agent is not found (404), ambiguous (409), or has no live gateway (502).

**Non-Goals:**
- Gateway attach/detach lifecycle management — the passive server does not attach or detach gateways. That remains `houmao-mgr`'s responsibility (per the greenfield design, Option A).
- TUI control endpoints (`/v1/control/tui/*`, `/v1/control/send-keys`) — these are TUI observation and control features covered by future steps.
- Headless control endpoints (`/v1/control/headless/state`) — future step.
- Mail notifier management (`/v1/mail-notifier`) — can be added later if needed.
- Caching or connection pooling for `GatewayClient` — not needed at current scale. A new client is created per request.

## Decisions

### 1. Gateway client is created per-request from registry record coordinates

For each proxy request, the service resolves the agent from the discovery index, extracts `gateway.host` and `gateway.port` from the registry record, creates a `GatewayClient(endpoint=GatewayEndpoint(host, port))`, and calls the appropriate method.

No client caching or pooling. Gateway coordinates can change between requests (agent detaches/reattaches), so creating a fresh client ensures we always use the current coordinates from the discovery index.

**Alternative considered:** Cache `GatewayClient` per agent_id. Rejected because coordinates can become stale if the gateway restarts on a different port, and the overhead of creating a `GatewayClient` (no connections opened until a request is made) is negligible.

### 2. Missing or detached gateway returns HTTP 502

If the agent is found but has no live gateway (`gateway` is `None` or `host`/`port` are `None`), the endpoint returns 502 Bad Gateway with a descriptive message. This is semantically correct: the passive server cannot fulfill the proxy request because the upstream gateway is unavailable.

If the `GatewayClient` call raises `GatewayHttpError` (gateway unreachable, timeout, or error response), the passive server returns 502 with the error detail forwarded.

### 3. Agent resolution reuses the existing `resolve_agent()` pattern

The gateway proxy endpoints use the same `{agent_ref}` path parameter and resolution logic as `GET /houmao/agents/{agent_ref}`: try `agent_id` first, then `agent_name`. Returns 404 or 409 as appropriate. This is extracted into a shared helper to avoid duplication.

### 4. Request/response models are reused directly from `gateway_models`

The proxy endpoints accept and return the exact same Pydantic models used by `GatewayClient`: `GatewayStatusV1`, `GatewayRequestCreateV1`, `GatewayAcceptedRequestV1`, `GatewayMailStatusV1`, `GatewayMailCheckRequestV1`, `GatewayMailCheckResponseV1`, `GatewayMailSendRequestV1`, `GatewayMailReplyRequestV1`, `GatewayMailActionResponseV1`. No wrapper or adapter models needed.

### 5. Proxy logic lives in service methods, not a separate module

The proxy methods are added to `PassiveServerService` directly (e.g., `gateway_status(agent_ref)`, `gateway_create_request(agent_ref, payload)`). Each method: resolves the agent, builds a `GatewayClient`, calls the gateway, and returns the result or raises an error. This keeps the code co-located with the other service methods and avoids a separate module for what is ~60 lines of straightforward forwarding logic.

## Risks / Trade-offs

- **Gateway coordinate staleness:** Between discovery poll cycles (default 5s), the registry record's gateway coordinates could become stale if the gateway restarts. Mitigation: `GatewayClient` calls will fail with `GatewayHttpError`, which is surfaced as 502. The next discovery cycle will update the index.
- **Timeout propagation:** The `GatewayClient` default timeout is 5 seconds. Long-running gateway operations (mail send with large attachments) may time out. Mitigation: acceptable for the initial version. A per-endpoint timeout override can be added later if needed.
- **Error detail leakage:** Gateway error responses are forwarded to the caller. This is intentional — the passive server is a transparent proxy, not a security boundary. Both the passive server and the gateway run on the same host.
