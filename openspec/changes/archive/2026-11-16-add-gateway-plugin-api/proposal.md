# Proposal

## Why

External applications need to extend a per-agent gateway without editing Houmao or importing gateway implementation details. GitHub [issue #76](https://github.com/igamenovoer/houmao/issues/76) establishes this extension contract before the CCCC chat and deferred Mail integrations in #77 and #78.

## What Changes

- Ship a versioned public Python SDK at `houmao.gateway.plugins` for trusted plugin packages, definitions, typed configuration, owner context, lifecycle, status, supervised workers, and ordinary-event admission.
- Discover installed implementations through the `houmao.gateway_plugins` entry-point group. Load only implementations explicitly enabled for a gateway, using that gateway process's Python environment; reject ambiguous registrations and unsupported SDK versions explicitly.
- Add typed Python launch/attach inputs and a maintained `houmao-mgr` gateway-attach configuration-file option. Persist resolved instance selections and credential references so foreground and detached gateway restarts restore the same configuration.
- Assign HTTP namespaces centrally at `/v1/plugins/{instance_id}/`. Validate the entire candidate route set before activation, including equivalent parameterized paths and overlapping catch-all routes. Quarantine every conflicting plugin instance while preserving core routes and unrelated plugins; reject malformed configuration, including duplicate keys, before applying it.
- Bind plugin context, private state, selected credential access, and service identity to the gateway owner. Ordinary route callers cannot select another sender or obtain operator control or service-administration operations through the SDK.
- Supervise asynchronous startup, workers, reconnect reporting, cancellation, and cleanup. Keep core health and operator control available when a plugin fails; expose sanitized per-instance status independently of core status.
- Dispatch ordinary events immediately only when the gateway, plugin, and agent body are ready. Return retryable errors when delivery cannot start; the sender retains the message and owns retry timing. Preserve existing readiness, pending-input, hook, and execution guards without accepting a deferred notification.
- Keep a message request in flight through its dispatch confirmation. If the addressed body dies, changes incarnation, or dispatch fails before the response, return an error and discard the delivery attempt. The gateway does not cache, queue, or resend the message after recovery.
- Define gateway restart as the boundary for plugin code and immutable configuration changes. Loaded plugins may connect, reconnect, refresh their already selected credential source, and detach from their configured service without restarting the agent body.
- Provide a separately installable example, hermetic external-wheel qualification, failure/recovery tests, and author/operator documentation.

## Capabilities

### New Capabilities

- `gateway-plugin-api`: External package discovery, public SDK, explicit instance configuration, owner binding, route registration, supervised lifecycle, and immediate ordinary-event dispatch with sender-owned retries.

### Modified Capabilities

- `agent-gateway`: Load persisted plugin instances through normal gateway launches; publish plugin status; gate immediate event dispatch on readiness and current-body continuity; preserve core availability and listener policy during plugin failures.

## Impact

- **Distro:** new SDK modules under `src/houmao/gateway/plugins/`, internal host integration under `src/houmao/agents/realm_controller/`, gateway configuration/client models, readiness and dispatch-confirmation seams, runtime launch/attach plumbing, and scoped manager gateway commands.
- **CI:** plugin contract, route-conflict, credentials, lifecycle, admission, and external-package tests under `tests/unit/` and `tests/integration/`; synthetic packages under `tests/fixtures/gateway-plugins/`.
- **Examples and docs:** a standalone sample under `examples/gateway-plugin/`, gateway authoring/operation references, CLI documentation, and system-file descriptions.
- **Dependencies:** use standard-library package metadata and asynchronous lifecycle primitives plus existing FastAPI/Pydantic dependencies. Add no plugin framework or separate SDK distribution in this change.

This change excludes gateway-side message caching, durable notification inboxes, automatic resend, delivery-receipt ledgers, new reconciliation machinery, queue-schema changes, untrusted-code isolation, a plugin RPC protocol, arbitrary live code replacement, remote authentication from #84, actual CCCC adapters, broad public lifecycle SDK work from #69, and automatic service/account provisioning. First-release plugin service routes are available only on loopback listeners. A lost response after dispatch can cause duplicates when the sender retries; this change does not promise exactly-once delivery.
