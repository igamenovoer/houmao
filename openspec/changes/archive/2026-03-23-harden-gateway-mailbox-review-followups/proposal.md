## Why

The review for `gateway-first-headless-mailbox-turns` identified a small set of follow-up issues in the new gateway mailbox path that are worth addressing before more work builds on that surface. The remaining work is narrow but important: remove unchecked type erasure in gateway mailbox normalization, make the one-way `read=true` v1 contract more explicit in local code, and harden the Stalwart read-state acknowledgment path so it does not rely on implicit inference.

## What Changes

- Narrow gateway mailbox principal and attachment normalization helpers to the concrete mailbox protocol models they actually consume instead of accepting `object` and relying on unchecked `getattr`.
- Clarify in the gateway mail-state request model and nearby code comments that v1 intentionally supports only the bounded "mark one processed message read" flow with `read=true`, while internal adapter signatures may remain broader for transport parity.
- Harden the Stalwart-backed mail-state acknowledgment path so the gateway validates normalized transport read-state evidence before returning `read` in the shared `/v1/mail/state` acknowledgment.
- Document the Stalwart `read` <-> JMAP `keywords/$seen` mapping inline and add focused tests that cover the hardening path.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `agent-gateway`: tighten the shared mailbox state-update acknowledgment contract so the gateway validates normalized transport read-state evidence instead of inferring an acknowledgment from missing fields.

## Impact

- Affected code:
  - `src/houmao/agents/realm_controller/gateway_mailbox.py`
  - `src/houmao/agents/realm_controller/gateway_models.py`
  - `src/houmao/mailbox/stalwart.py`
  - `tests/unit/agents/realm_controller/test_gateway_support.py`
- Affected APIs:
  - `POST /v1/mail/state` error behavior for malformed transport normalization becomes explicit instead of inferred
- Affected systems:
  - gateway mailbox adapter normalization
  - Stalwart-backed shared mailbox state updates
