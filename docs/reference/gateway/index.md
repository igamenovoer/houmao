# Agent Gateway Reference

This section explains the optional per-agent gateway sidecar: what it adds to a runtime-managed session, how it is discovered, and how its queue, status, and recovery model work.

If you are new to the subsystem, start with lifecycle. If you need exact payloads and file contracts, go to contracts. If you are debugging queue or recovery behavior, use the internals page.

## Mental Model

The gateway is an optional control plane attached to one runtime-managed session.

- A session can be gateway-capable without having a live gateway process attached.
- Stable attachability is published into the session root and tmux env even before the first live attach.
- When a live gateway exists, it exposes a small HTTP surface and durable queue for that same logical session.
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

### Contracts

- [Protocol And State Contracts](contracts/protocol-and-state.md): Attach metadata, env vars, HTTP routes, status fields, and durable gateway artifacts.

### Internals

- [Queue And Recovery](internals/queue-and-recovery.md): Queue storage, current-instance state, epochs, restart recovery, and replay blocking.

## Related References

- [Runtime-Managed Agents Reference](../agents/index.md): The broader runtime session model that the gateway attaches to.
- [Brain Launch Runtime](../brain_launch_runtime.md): Overview page plus backend-specific notes.
- [Mailbox Reference](../mailbox/index.md): Separate async message transport and runtime mailbox docs.

## Source References

- [`src/gig_agents/agents/brain_launch_runtime/gateway_models.py`](../../../src/gig_agents/agents/brain_launch_runtime/gateway_models.py)
- [`src/gig_agents/agents/brain_launch_runtime/gateway_storage.py`](../../../src/gig_agents/agents/brain_launch_runtime/gateway_storage.py)
- [`src/gig_agents/agents/brain_launch_runtime/gateway_service.py`](../../../src/gig_agents/agents/brain_launch_runtime/gateway_service.py)
- [`src/gig_agents/agents/brain_launch_runtime/gateway_client.py`](../../../src/gig_agents/agents/brain_launch_runtime/gateway_client.py)
- [`src/gig_agents/agents/brain_launch_runtime/runtime.py`](../../../src/gig_agents/agents/brain_launch_runtime/runtime.py)
- [`tests/unit/agents/brain_launch_runtime/test_gateway_support.py`](../../../tests/unit/agents/brain_launch_runtime/test_gateway_support.py)
