# Proposal

## Why

Already-running Houmao agents need to participate in an independently operated CCCC service without installing MCP into their bodies or surrendering lifecycle control. The gateway plugin SDK is implemented, but the inspected CCCC 0.4.56 interfaces do not yet provide a generic authenticated receiver with Houmao's confirmed-handoff contract.

## What Changes

- Deliver issue [#77](https://github.com/igamenovoer/houmao/issues/77) through an independently installable `houmao-cccc` distribution using only the public `houmao.gateway.plugins` SDK. No new plugin framework is required.
- Bind each configured instance to the gateway owner's stable agent ID and a preprovisioned CCCC endpoint, Group, Actor, and Actor registration generation. Keep CCCC addressing separate from offline/online email and canonical mail identity.
- Attach the integration through existing operator-selected gateway configuration without restarting the agent body. Reconnect, disconnect, and refresh the selected private credential source within that immutable binding.
- Establish a versioned CCCC-side external receiver interface with fixed-actor authentication, fenced receiver leases, bounded delivery offers, and authoritative delivery outcomes. Crash recovery waits for an existing lease to expire unless a CCCC operator explicitly takes over. Deliver any required upstream changes as a pinned, reproducible dependency or tracked compatibility patch series, never solely inside `extern/orphan/cccc`.
- Expose owner-bound chat send, reply, explicit delivery retry, bounded non-consuming history, membership inspection, capabilities, and delivery status through the plugin namespace and a thin CLI.
- Dispatch incoming ordinary chat immediately through gateway readiness admission. Return refusal or uncertainty on busy/unavailable bodies, death, restart, or deadline expiry; keep message retention and fresh retry decisions on the sending CCCC side.
- Reconcile provider receipts and observation cursors after reconnect without replaying history into the body. Require a small chat receive/reply smoke with two real managed coding agents before issue #77 closure, alongside deterministic stand-in tests and actual-provider qualification. Publish a runnable native Pixi deployment example.

## Capabilities

### New Capabilities

- `cccc-gateway-binding`: Independent plugin installation, owner-bound CCCC identity, selected credentials, connection lifecycle, isolated state, and safe status.
- `cccc-external-receiver`: Versioned provider authentication, receiver fencing, bounded delivery attempts, confirmed outcomes, and sender-owned retry.
- `cccc-chat`: Actor-scoped send/reply/retry, native event references, bounded history, membership, capability inspection, and delivery receipts.

### Modified Capabilities

None. This change consumes the completed `add-gateway-plugin-api` contract and existing agent/email identity contracts without changing them.

## Impact

The optional released distribution belongs in `packages/houmao-cccc/`, a new explicitly classified distro location with its own wheel metadata; implementation must document that location and include it in contributor checks without including it in Houmao's core wheel. A required CCCC patch series belongs under `extern/tracked/cccc-receiver/`; native build/operation support remains in `tools/cccc/`. Add CI coverage under `tests/unit/gateway_plugins/` and `tests/integration/cccc/`, qualification utilities under `scripts/qualification/cccc/`, and supported integration documentation and examples.

The inspected reference is `ChesterRa/cccc` at `d12732ebd6dfdbc260a59a286bd5e510d04d4832`. Stock service startup is preparation, not receiver compatibility evidence. Issue #76's completed artifacts must be synchronized before this change is implemented. This change precedes `cccc-02-add-explicit-deferred-mail`; authenticated public gateway exposure (#84), account provisioning, automatic chat replay, deferred Mail operations, arbitrary remote process control, and browser-managed actors are outside this change.
