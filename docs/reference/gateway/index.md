# Agent Gateway Reference

This section explains the optional per-agent gateway sidecar: what it adds to a runtime-managed session, how it is discovered, and how its queue, status, recovery model, and shared mailbox facade work.

If you are new to the subsystem, start with lifecycle. If you need exact payloads and file contracts, go to contracts. If you are debugging queue or recovery behavior, use the internals page.

## Mental Model

The gateway is an optional control plane attached to one runtime-managed session.

- A session can be gateway-capable without having a live gateway process attached.
- Stable attachability is published into the session root and tmux env even before the first live attach.
- When a live gateway exists, it exposes a small HTTP surface, a durable queue, and optionally a shared mailbox facade for that same logical session.
- Gateway-local health is intentionally separate from managed-agent availability.

## Key Terms

- `gateway-capable session`: A runtime-managed tmux-backed session that has stable attach metadata and seeded gateway state.
- `live gateway`: A currently running gateway sidecar with live host and port bindings.
- `attach contract`: The strict `attach.json` payload that tells the system how to attach to one session.
- `desired listener`: The host or port the gateway should try to reuse on later starts.
- `managed-agent epoch`: The gateway's generation counter for the current upstream instance behind the same logical session.
- `reconciliation`: The state where the logical session still exists, but the upstream instance changed and queued work must not be replayed blindly.

## Read By Goal

### Start here

- [Lifecycle And Operator Flows](operations/lifecycle.md): Attach, inspect, detach, and understand offline versus live gateway states.
- [Gateway Troubleshooting](operations/troubleshooting.md): Diagnose pair-managed current-session attach failures, stale gateway metadata, and reserved-window safety checks.
- [Gateway Mailbox Facade](operations/mailbox-facade.md): Understand `/v1/mail/*`, adapter selection from the session manifest, loopback-only availability, and notifier behavior through the shared mailbox abstraction.

### Contracts

- [Protocol And State Contracts](contracts/protocol-and-state.md): Attach metadata, env vars, HTTP routes, status fields, and durable gateway artifacts.

### Internals

- [Queue And Recovery](internals/queue-and-recovery.md): Queue storage, current-instance state, epochs, restart recovery, and replay blocking.

## Related References

- [Runtime-Managed Agents Reference](../agents/index.md): The broader runtime session model that the gateway attaches to.
- [Managed-Agent API](../managed_agent_api.md): The server-owned `/houmao/agents/*` contract for detail state, transport-neutral request submission, and managed-agent gateway lifecycle.
- [Realm Controller](../realm_controller.md): Overview page plus backend-specific notes.
- [Mailbox Reference](../mailbox/index.md): Separate async message transport and runtime mailbox docs.
- [Agents And Runtime](../system-files/agents-and-runtime.md): Runtime-managed session roots, nested gateway artifacts, and Stalwart credential material outside the mailbox transport-owned storage model.

## Source References

- [`src/houmao/agents/realm_controller/gateway_models.py`](../../../src/houmao/agents/realm_controller/gateway_models.py)
- [`src/houmao/agents/realm_controller/gateway_storage.py`](../../../src/houmao/agents/realm_controller/gateway_storage.py)
- [`src/houmao/agents/realm_controller/gateway_service.py`](../../../src/houmao/agents/realm_controller/gateway_service.py)
- [`src/houmao/agents/realm_controller/gateway_client.py`](../../../src/houmao/agents/realm_controller/gateway_client.py)
- [`src/houmao/agents/realm_controller/runtime.py`](../../../src/houmao/agents/realm_controller/runtime.py)
- [`tests/unit/agents/realm_controller/test_gateway_support.py`](../../../tests/unit/agents/realm_controller/test_gateway_support.py)
