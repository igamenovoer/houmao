## Why

Sending mailbox messages to a Houmao-managed agent currently assumes the message is being sent as a real mailbox participant, which is inconvenient when the operator only wants to leave a one-way note for the agent and does not expect a reply. Houmao needs a filesystem-first operator-origin mail path that preserves real sender provenance without forcing operators to provision or invent a personal mailbox identity.

## What Changes

- Add a filesystem-first operator-origin mailbox delivery capability for sending one-way notes to a managed agent mailbox without pretending the operator is the managed agent sender.
- Introduce a reserved Houmao-owned sender identity `HOUMAO-operator@houmao.localhost` for operator-origin one-way mail.
- **BREAKING** Adopt the default mailbox-address policy `<agentname>@houmao.localhost` for newly derived managed-agent mailboxes while reserving any local part that begins with `HOUMAO-` for system use only.
- Add a distinct operator-origin mail action, transport-aware gateway route, and manager/server-facing proxy surfaces instead of weakening the existing `send as the managed agent` behavior.
- Limit v1 support for operator-origin mail to the filesystem mailbox transport and require explicit unsupported semantics for `stalwart`.
- Update CLI and mailbox reference docs to explain the new operator-origin lane, the reserved address namespace, the filesystem-first scope, and the `stalwart` stub boundary.

## Capabilities

### New Capabilities
- `agent-mailbox-operator-origin-send`: reserved Houmao-owned one-way operator-origin mailbox delivery for filesystem-backed mailboxes.

### Modified Capabilities
- `agent-mailbox-protocol`: mailbox principal addressing and reserved-address rules change to support `<agentname>@houmao.localhost` defaults and the reserved `HOUMAO-*` sender namespace.
- `agent-mailbox-fs-transport`: filesystem mailbox bootstrap, registration, and delivery rules change to provision and protect the reserved operator mailbox account and support operator-origin delivery semantics.
- `agent-gateway`: shared `/v1/mail/*` gateway surface changes to expose operator-origin mailbox delivery and explicit unsupported semantics when the resolved transport is not filesystem.
- `houmao-srv-ctrl-native-cli`: native `houmao-mgr agents mail ...` behavior changes to expose a distinct operator-origin mailbox action instead of overloading existing `send` semantics.
- `houmao-mgr-mailbox-cli`: mailbox-root bootstrap and mailbox-account lifecycle semantics change to provision and protect the reserved `HOUMAO-operator@houmao.localhost` account.
- `houmao-mgr-project-mailbox-cli`: project-local mailbox-root bootstrap and mailbox-account lifecycle semantics change to mirror the reserved operator-account behavior.
- `passive-server-gateway-proxy`: managed-agent mail proxy behavior changes to forward the new operator-origin mailbox action through the gateway-backed mail surface.
- `docs-cli-reference`: CLI reference coverage changes to document the new operator-origin mailbox command, reserved address policy, and filesystem-only support boundary.
- `mailbox-reference-docs`: mailbox subsystem reference changes to document the reserved operator sender, the `<agentname>@houmao.localhost` default address policy, and the `stalwart` stub boundary for operator-origin mail.

## Impact

- Affected mailbox protocol and filesystem transport code under `src/houmao/mailbox/`.
- Affected gateway models, client, and service code under `src/houmao/agents/realm_controller/`.
- Affected operator-facing mail routing and mailbox-root administration under `src/houmao/srv_ctrl/commands/`, plus managed-agent server and passive-server mail proxy surfaces.
- Affected CLI and mailbox reference docs for the new command, naming policy, and transport boundary.
- No `stalwart` operator-origin delivery implementation is included in this change; `stalwart` stays an explicit unsupported stub for this feature in v1.
