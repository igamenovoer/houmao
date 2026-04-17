## 1. Gateway Client Proxy Policy

- [x] 1.1 Add a gateway-owned proxy policy resolver that treats `HOUMAO_GATEWAY_RESPECT_PROXY_ENV=1` as the only opt-in to environment proxy handling.
- [x] 1.2 Update `GatewayClient` so direct loopback HTTP is the default and proxy-aware HTTP is used only when the gateway proxy env opt-in is active at client construction.
- [x] 1.3 Ensure the default direct path does not mutate `NO_PROXY`, `no_proxy`, or other process-wide proxy environment values.

## 2. Attach Readiness Diagnostics

- [x] 2.1 Preserve the last `GatewayHttpError` observed during same-session gateway health polling.
- [x] 2.2 Preserve the last `GatewayHttpError` observed during detached-process gateway health polling.
- [x] 2.3 Include the last health probe error detail in attach timeout messages when one exists.

## 3. Tests

- [x] 3.1 Add gateway client coverage proving loopback health succeeds with bogus proxy variables and no loopback `NO_PROXY`.
- [x] 3.2 Add gateway client coverage proving `HOUMAO_GATEWAY_RESPECT_PROXY_ENV=1` uses environment proxy handling.
- [x] 3.3 Add attach readiness coverage proving timeout diagnostics include the last health probe error.
- [x] 3.4 Run targeted gateway client and gateway attach tests.
- [x] 3.5 Run `pixi run lint`, `pixi run typecheck`, and `pixi run test`.

## 4. Documentation

- [x] 4.1 Document `HOUMAO_GATEWAY_RESPECT_PROXY_ENV` in the appropriate gateway or system environment reference.
- [x] 4.2 Ensure docs distinguish gateway proxy opt-in from existing CAO `NO_PROXY` preservation behavior.
