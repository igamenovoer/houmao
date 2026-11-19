# Proposal

## Why

Codex already provides a persistent app-server, but Houmao deliberately rejects its old adapter. That adapter skips initialization and submits an obsolete turn request shape.

## What Changes

- **BREAKING** Replace the blanket rejection for fresh qualified `(codex, service)` launches with a `codex_app_server` adapter using the shared service owner.
- Initialize the native connection, start or resume the selected thread, submit typed input, correlate notifications to thread and turn, and interrupt only the intended active turn.
- Preserve explicit backend selection, current-schema-only ownership, per-agent isolation, and permission policy. Enable the pair through normal manager and gateway operations after native qualification.

## Capabilities

### New Capabilities

- `codex-app-server-control` defines managed app-server negotiation, thread selection, turn settlement, and recovery.

### Modified Capabilities

- `brain-launch-runtime` replaces the retired app-server prohibition with fresh, qualified service selection.

## Impact

Affects the Codex runtime factory, app-server client, launch policy, discovery/capability registration, fixture coverage, and docs. Legacy manifests supply no live process authority.

## Dependencies

Direct prerequisite for implementation and spec synchronization is `run-modes-04-add-persistent-service-runtime`. Can proceed alongside 05. The shared owner is protocol-independent.
