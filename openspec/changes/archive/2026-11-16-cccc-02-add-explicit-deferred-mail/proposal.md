# Proposal

## Why

CCCC's deferred Mail provides actor-to-actor correspondence that callers should be able to select while Stalwart is healthy or unavailable. Its consuming, ordered-batch read cursor differs from Houmao email semantics, so reusing the email slots or silently retrying reads would misrepresent identity, delivery, and consumption.

## What Changes

- Deliver issue [#78](https://github.com/igamenovoer/houmao/issues/78) by extending the same installed `houmao-cccc` plugin and CCCC-side interface introduced by `cccc-01-add-owner-bound-chat-plugin`.
- Expose explicitly selected Mail send/reply, bounded non-consuming peek and status, consuming next-batch read, and read-outcome reconciliation under the owner's existing CCCC Group/Actor binding.
- Preserve CCCC append order and authoritative Mail cursor. Add provider-side read operation IDs and durable boundary receipts so a lost response can be reconciled without consuming another batch or creating a gateway payload cache.
- Negotiate message-count and byte limits before consumption, reject stale cursor preconditions and binding references, and report unsupported operations and recipient types explicitly.
- Keep CCCC Mail outside `mailboxes.offline` and `mailboxes.online`. Preserve online-first canonical email identity, ordinary email reminder behavior, and independent Stalwart availability.
- Keep Mail deferred. Route CCCC's bounded content-free Mail notices through ordinary gateway admission without reading the inbox, importing email archive/compaction rules, or acquiring interrupt authority.
- Qualify explicit CCCC use during Stalwart failure, cursor/reconnection behavior, response-loss recovery, actor isolation, and the installed-package boundary. Require a small deferred Mail send/read/reply smoke with two real managed coding agents before issue #78 closure, alongside deterministic stand-in tests. Document actor addresses and provider receipts separately from standard email semantics.

## Capabilities

### New Capabilities

- `cccc-deferred-mail`: Explicit CCCC Mail operations, recipient scope, bounded ordered consumption, non-consuming inspection, authoritative read reconciliation, capability limits, and deferred notices.

### Modified Capabilities

None. The change adds Mail operations to the extensible connection/capability contract established by change 01. It preserves the existing email channel contracts and the generic immediate-dispatch SDK.

## Impact

Extend the optional `packages/houmao-cccc/` distribution, the qualified CCCC receiver source/patch dependency, `tests/unit/gateway_plugins/`, `tests/integration/cccc/`, `scripts/qualification/cccc/`, the deployment example, and integration/agent guidance. CCCC remains authoritative for messages, read receipts, and cursor recovery; the gateway stores no Mail body mirror or deferred resend queue.

Implementation requires change 01 to be completed, qualified, and synchronized into main specs first; the numbered names alone do not enforce that prerequisite. Stock CCCC 0.4.56 has consuming inbox reads but does not provide the proposed read-operation reconciliation interface. This change includes that provider extension and must not advertise Mail read support before it is qualified. Automatic failover/mirroring, a third email slot, arbitrary external-email delivery, per-message email archive emulation, and a new messaging store are outside scope.
