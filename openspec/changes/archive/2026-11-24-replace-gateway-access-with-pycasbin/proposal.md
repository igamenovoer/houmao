# Proposal

## Why

Houmao currently assigns broad access by route class and implements additional exceptions in handlers. Per-caller grants for peer edits and other resources need one authorization model that also covers existing control, mailbox, browser, plugin, and passive server operations.

## What Changes

- Evaluate verified caller, target ownership scope, resource, and action with PyCasbin inside the existing Houmao processes. Support exact grants and target-scoped roles for people, agents, and services. A logical agent can receive a grant across OS accounts, containers, or hosts regardless of its current execution.
- Keep OpenSSH SSHSIG request proof and the valid-empty-admin-roster rule. Gateway-admin authorizes every supported client-facing operation on its target. An empty roster gives every caller that role. First-key registration closes anonymous admin access and removal of the final admin reopens it.
- Add owner-local policy administration and authenticated live admin enrollment per SSH key. An ordinary key uses its principal's scoped grants on a keyed target, even when another key for that principal is an admin. Keep local execution ownership and internal service authority tied to their verified bindings.
- Carry permissions through gateway and detached passive operations, relays, browser tickets, AG-UI streams, and host-managed plugin routes. Recheck sensitive work at its effect boundary.
- **BREAKING** Replace the roster and route-class schemas, proof and discovery contracts, key-management commands and routes, and plugin access declarations. Existing installations must explicitly reprovision authorization data and update callers and plugins. Older authorization state fails closed.

## Capabilities

### New Capabilities

- `agent-authorization-policy` defines principals, domain-scoped policy, lifecycle, administration, and current authorization at protected effects.

### Modified Capabilities

- `authenticated-gateway-access` applies current policy to verified SSHSIG callers, open access, and challenge and error handling.
- `agent-gateway` declares semantic operations for HTTP admission, mailbox access, and endpoint discovery.
- `agent-discovery-registry` publishes the new secret-free gateway authorization descriptor.
- `passive-server-gateway-proxy` applies the owner policy to direct and relayed operations.
- `passive-server-request-submission` authorizes submission, interruption, and stop against the selected target.
- `gateway-web-entry` checks the browser entry permission through proof, approval, and redemption.
- `gateway-dashboard` guides browsers through the current owner-local entry policy.
- `per-agent-ag-ui-attachment` checks operation-specific authority and live stream permissions.
- `ag-ui-workbench-local-server` signs protected requests with the current local operator's explicitly selected key.
- `ag-ui-workbench-agent-picker` keeps operator signer bindings independent of editable gateway URLs.
- `ag-ui-workbench-app` distinguishes a protected pane's authorization refusal from a reconnectable transport failure.
- `ag-ui-workbench-client-event-cache` verifies replacement listener bindings for signed streams and surfaces authorization refusals.
- `gateway-plugin-api` gives plugins host-validated instance-specific operation declarations.
- `houmao-mgr-agents-scope-cli` provides selected-agent access administration and a managed caller's public signing identity.
- `houmao-srv-ctrl-native-cli` selects browser entry credentials through the new proof and policy contract.
- `agent-gateway-reference-docs` describes authorization, enrollment, discovery, and the manual cutover.

## Impact

Houmao adds the PyPI distribution `pycasbin` through Pixi as a packaged runtime dependency. The gateway, passive server, manager CLI, SDK and bundled consumers adopt one owner-private policy source. The `add-versioned-agent-file-edits` proposal uses this policy interface for file operations and records the admitted agent as commit author.
