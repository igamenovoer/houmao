# Proposal

## Why

ACP serves multiple requests while its stdio connection stays open. RC2 closes that connection after every turn, so independent CLI calls cannot share a running ACP service.

## What Changes

- Add a per-agent service owner inside the admitted execution context. It keeps the native control connection across manager exit, gateway detach, and passive-server restart.
- Implement `(dsh, service)` with `dsh_acp` as the first persistent adapter. Bind one live process incarnation, native conversation, and active operation to the managed generation.
- Distinguish client detach, turn interrupt, provider stop, and explicit recovery. Reconcile uncertain input by its original identity and fence stale control.
- Qualify persistent DSH configuration, request-scoped overrides, MCP activation, and journal evidence with actual multi-turn runs. Publish only verified native refresh boundaries.

## Capabilities

### New Capabilities

- `managed-agent-service-runtime` owns persistent provider control, native readiness, operation correlation, and recovery.
- `dsh-acp-service-control` binds DSH ACP sessions, negotiated controls, and evidence to that service owner.

### Modified Capabilities

- `agent-gateway` dispatches ACP work to the already running service and uses its readiness for mail and plugins.
- `brain-launch-runtime` includes service mode in DSH's qualified permission policy.
- `native-agent-home-refresh` scopes DSH automatic discovery and service refresh to observed boundaries.

## Impact

Affects runtime lifecycle, service supervisor, gateway attach metadata and adapters, DSH ACP protocol code, launch policy, current-home refresh, and integration fixtures. The owner uses the existing managed tmux envelope for process supervision.

## Dependencies

Direct prerequisite for implementation and spec synchronization is `run-modes-02-unify-managed-agent-control`. Can proceed alongside 03 and 07. The DSH cutover ships after 01 through 04 pass. Changes 05 and 06 depend on this owner.
