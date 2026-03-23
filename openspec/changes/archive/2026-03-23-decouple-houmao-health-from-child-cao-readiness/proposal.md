## Why

`houmao-server` currently exposes child-CAO health metadata even when it is started in `--no-startup-child` mode, and at least one native-headless demo treats that metadata as a startup readiness requirement. That coupling breaks valid no-child workflows and contradicts the intended contract that Houmao root health and child-CAO health are distinct signals.

## What Changes

- Clarify the `houmao-server` root health contract so functionality that does not depend on the child CAO server can treat `GET /health` as Houmao-server readiness without requiring child-CAO health.
- Define the no-child (`startup_child=false`) behavior for Houmao-owned health and current-instance payloads so callers can distinguish "child intentionally absent" from "child unhealthy".
- Update the mail ping-pong gateway demo startup contract so its managed-headless startup path does not block on child-CAO health when the demo explicitly starts `houmao-server` with `--no-startup-child`.
- Add verification coverage for both server-level no-child health semantics and the affected demo startup expectation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-server`: root health and current-instance semantics for no-child mode, including how child-CAO metadata is exposed when `startup_child=false`
- `mail-ping-pong-gateway-demo-pack`: startup readiness for the managed-headless demo-owned `houmao-server` path when the demo does not start a child CAO server

## Impact

- Affected code: `src/houmao/server/`, `src/houmao/demo/mail_ping_pong_gateway_demo_pack/`
- Affected tests: `tests/unit/server/`, `tests/unit/demo/`, and any integration coverage that verifies no-child managed-headless flows
- Affected APIs: `GET /health` and `GET /houmao/server/current-instance`
- No new external dependencies
