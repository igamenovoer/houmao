## Why

The repository already has the pieces needed for real gateway-to-email interactions over the Stalwart email system: a local Stalwart and Cypht stack, a Stalwart-backed mailbox transport, and a gateway-owned unread-mail notifier. What is missing is one reproducible interactive demo that brings those pieces together with multiple real mailbox accounts, lets an operator inspect mail through Cypht, and proves that gateway wake-up behavior stays tied to unread mail only. For this change, the scope is intentionally limited to the Stalwart email-system path and does not attempt to cover the filesystem mailbox transport.

## What Changes

- Add a new interactive demo pack under `scripts/demo/` for real Stalwart-backed gateway-to-email workflows with Cypht as the operator inspection surface.
- Bring up the repository-owned local email stack, ensure at least two pre-made mailbox accounts such as `alice@example.test` and `bob@example.test`, and use those accounts as the backing mailbox identities for two live gateway-managed sessions.
- Start two mailbox-enabled sessions plus two attached gateways, one bound to Alice and one bound to Bob, using the `stalwart` mailbox transport.
- Provide stateful demo commands that let an operator start the environment, send mail from one gateway-backed session to the other, inspect gateway and mailbox state, continue the exchange for multiple turns, and stop the environment cleanly.
- Make the receiver-side interactive story explicit: when unread mail arrives, the receiver flow should surface the unread message content in a stable demo-visible way without relying on direct Stalwart-native objects or ad hoc mailbox inspection.
- Verify the unread-only notifier contract in this real-email setting: gateways notify only for unread mail, do not auto-mark mail as read, and deduplicate unchanged unread sets across poll cycles.
- Capture stable demo-owned artifacts for session start, gateway attach, mail sends, unread checks, notifier state, and operator inspection so the demo is usable both manually and as a future regression surface.

## Capabilities

### New Capabilities
- `gateway-stalwart-cypht-interactive-demo-pack`: Defines the repository-owned interactive demo pack that exercises two Stalwart-backed gateway sessions with pre-provisioned mailboxes and Cypht-based operator inspection, with no filesystem-mailbox variant in this version.

### Modified Capabilities
- None.

## Impact

- Affected code: new content under `scripts/demo/` for the Stalwart-only interactive demo pack, its helper scripts, and any narrow fixture or role-package additions needed to run the receiver-side unread-message workflow; no filesystem-demo changes are part of this version.
- Affected systems: `dockers/email-system/`, Stalwart-backed mailbox session startup, live gateway attach and notifier flows, Cypht operator inspection, and CAO-backed demo orchestration.
- Affected docs: the new demo-pack README plus any reference links that should point operators from gateway or mailbox docs to this interactive Stalwart demo.
- Affected tests: demo-pack helper coverage, pack-level verification or snapshot tests, and any targeted gateway or mailbox integration coverage needed for real unread-only multi-account behavior.
