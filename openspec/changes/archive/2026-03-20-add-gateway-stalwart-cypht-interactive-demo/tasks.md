## 1. Demo Pack Scaffold

- [x] 1.1 Create `scripts/demo/gateway-stalwart-cypht-interactive-demo-pack/` with `README.md`, `run_demo.sh`, tracked demo parameters, and pack-local helper scripts for stateful start, send, check, inspect, and stop flows, scoped only to the Stalwart email-system path.
- [x] 1.2 Define the pack-owned demo state and artifact layout so follow-up commands can target the same Alice and Bob sessions, gateways, stack settings, and prior turn history across multiple interactive turns.

## 2. Stack And Session Orchestration

- [x] 2.1 Implement demo start and stop helpers that bring up `dockers/email-system/`, verify stack health, and ensure the tracked Alice and Bob Stalwart mailbox accounts exist through `dockers/email-system/provision_stalwart.py`.
- [x] 2.2 Implement startup of two live mailbox-enabled sessions using `--mailbox-transport stalwart` with explicit mailbox address and login-identity overrides for Alice and Bob, without adding filesystem transport branching in this change.
- [x] 2.3 Implement gateway attach and persisted connection metadata for both sessions so each side exposes the loopback `/v1/mail/*` and `/v1/mail-notifier` surfaces during the demo.

## 3. Interactive Gateway Mail Workflows

- [x] 3.1 Implement the sender-side mail flow that sends a message from Alice to Bob or Bob to Alice through the sender gateway's shared mailbox facade rather than through direct Stalwart-native calls.
- [x] 3.2 Implement the receiver-side unread check or watch flow that queries the receiver gateway for unread mail and prints normalized message content, including sender, subject, message reference, and body text or preview, in a stable demo-visible format.
- [x] 3.3 Implement the inspect flow so the operator can review current gateway mailbox status, notifier status, and demo-owned turn or message history without re-creating the environment.
- [x] 3.4 Preserve and surface unread-only notifier semantics in the interactive flow, including unchanged-unread-set dedup behavior and the rule that read-state changes come from the real mail system rather than gateway bookkeeping.

## 4. Docs And Validation

- [x] 4.1 Write the demo-pack README with explicit Stalwart-only scope, Stalwart stack startup, Alice and Bob account credentials, Cypht login workflow, gateway send and unread-check commands, unread-only notifier semantics, and cleanup steps.
- [x] 4.2 Add targeted automated coverage for the pack helpers and any deterministic command, state, or report logic that can be validated without requiring a real browser session.
- [x] 4.3 Run targeted tests for the new demo pack and helper surfaces, then run `pixi run openspec validate --strict --json --type change add-gateway-stalwart-cypht-interactive-demo`.
