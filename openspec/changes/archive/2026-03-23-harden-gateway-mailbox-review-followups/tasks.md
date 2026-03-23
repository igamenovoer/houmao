## 1. Gateway Mailbox Hardening

- [x] 1.1 Narrow the gateway mailbox participant and attachment normalization helpers to concrete mailbox protocol models in `gateway_mailbox.py`, updating imports and signatures so the filesystem-backed path no longer relies on `object` plus unchecked `getattr`.
- [x] 1.2 Clarify the bounded v1 `read=true` contract in the local gateway mail-state model and add an inline Stalwart JMAP `$seen` mapping note near the transport state-update path.
- [x] 1.3 Harden the Stalwart-backed `/v1/mail/state` acknowledgment path so malformed normalized state without an explicit boolean `unread` signal raises `GatewayMailboxError` instead of inferring `read=true`.

## 2. Focused Verification

- [x] 2.1 Add or update unit coverage in `tests/unit/agents/realm_controller/test_gateway_support.py` for the hardened Stalwart state-update failure path and the preserved successful acknowledgment behavior.
- [x] 2.2 Run the focused gateway mailbox unit tests needed to verify the hardening change.
