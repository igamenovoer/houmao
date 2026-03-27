## 1. Live Mailbox Binding Infrastructure

- [x] 1.1 Add a runtime-owned live mailbox binding resolver for tmux-backed sessions that reads the targeted common and transport-specific mailbox binding vars and returns one normalized actionable binding payload.
- [x] 1.2 Add runtime helpers to publish, refresh, and clear the targeted mailbox binding vars in tmux session environment alongside durable mailbox manifest updates.
- [x] 1.3 Update mailbox activation-state bookkeeping so supported tmux-backed mailbox mutations become active after live projection refresh instead of requiring relaunch solely for mailbox binding refresh.

## 2. Runtime Mailbox Workflow Integration

- [x] 2.1 Update runtime-owned mailbox command preparation and readiness checks to resolve current mailbox bindings through the live resolver for tmux-backed sessions.
- [x] 2.2 Update projected mailbox system skill assets and supporting mailbox guidance to use the runtime-owned live resolver instead of telling agents to trust inherited process env or parse raw tmux state manually.
- [x] 2.3 Ensure transport-specific live prerequisites such as Stalwart session-local credential material are validated or materialized before a refreshed live mailbox binding is treated as actionable.

## 3. Gateway Notifier Integration

- [x] 3.1 Update gateway notifier support and enablement logic to combine manifest-backed durable mailbox capability with live tmux-backed mailbox actionability.
- [x] 3.2 Update notifier status and failure reporting so sessions with durable mailbox presence but incomplete live mailbox projection fail clearly without introducing a second persisted mailbox-capability store.
- [x] 3.3 Revise notifier reminder flows to rely on the updated mailbox skill contract for live mailbox work after late mailbox mutation.

## 4. Verification And Documentation

- [x] 4.1 Add unit coverage for tmux live mailbox binding resolution, tmux env refresh and clear behavior, and mailbox activation-state transitions after late mutation.
- [x] 4.2 Add integration coverage for late mailbox registration and notifier enablement on tmux-backed sessions without relaunch, including filesystem and Stalwart actionability checks where supported.
- [x] 4.3 Update mailbox and gateway docs to describe manifest as durable mailbox authority, tmux session env as live mailbox projection, and the removal of relaunch-only guidance for supported tmux-backed mailbox refresh flows.
