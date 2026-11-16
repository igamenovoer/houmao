# Proposal

## Why

After the dual-mail foundation, agents must consume externally provisioned online accounts without restarting their bodies, and Stalwart access must avoid scanning retained history or downloading bodies during discovery. GitHub [#79](https://github.com/igamenovoer/houmao/issues/79) and [#80](https://github.com/igamenovoer/houmao/issues/80) share binding lifecycle, account scope, and notifier state and should be implemented together.

This is change **02 of 02**. It depends on [mail-01-establish-identity-and-offline-mail](../2026-11-16-mail-01-establish-identity-and-offline-mail/proposal.md) being implemented, verified, and synchronized into main specs first. Its deltas extend that resulting contract, not the current single-mailbox implementation.

## What Changes

- Add supported CLI/API online attachment, credential refresh, reconnect, replacement, status, and detach for already-running agents. Accept mailbox-level credentials through protected references; management credentials and account provisioning are unnecessary.
- Validate candidates before revision-checked activation. Preserve the stable `agent_id` and offline binding, update derived canonical mail identity atomically, retire superseded workers, and prevent stale requests or references from targeting replacement accounts.
- **BREAKING:** Make shared mailbox listing a bounded metadata page with filter-bound cursors. Retrieve bodies only through explicit peek/read and report content limits clearly. Repair manager, gateway, passive-client, and skill consumers.
- Push supported filters to Stalwart, cache discovery and mailbox roles, and batch metadata requests. Treat unsupported filters and missing roles as explicit limitations rather than broadening queries.
- Persist account-scoped incremental JMAP checkpoints and bounded metadata views, with transactional checkpoint commits and bounded stale-state recovery. Keep query state distinct from email-object state.
- Preserve periodic reminders for unchanged eligible work. Suppress overlapping/same-cycle wakeups without permanent per-message notification suppression; preserve archive completion and one-shot compaction.
- Qualify live behavior with local private Stalwart credentials and document a load plan for roughly 100 agents and millions of retained messages, measuring requests, bytes, latency, memory, and backlog recovery.

## Capabilities

### New Capabilities

- `online-mail-attachment`: Owner-bound live online account attachment, credential resolution, revision fencing, reconnect, and cleanup.
- `stalwart-mailbox-sync`: Bounded server-filtered metadata pages, incremental JMAP state, recovery, and observable synchronization budgets.

### Modified Capabilities

- `agent-mailbox-stalwart-transport`: Separate account provisioning from attachment and preserve JMAP lifecycle semantics.
- `agent-mailbox-protocol`: Metadata-only bounded list pages and explicit body retrieval.
- `agent-gateway-mail-notifier`: Consume bounded synchronized views while preserving periodic reminders and readiness behavior.
- `passive-server-gateway-proxy`: Forward online binding controls, continuation cursors, and structured limitations without a second authority.
- `houmao-srv-ctrl-native-cli`: Online attachment/refresh/detach commands and bounded mailbox listing.
- `agent-mailbox-system-skills`: Paginated metadata triage and current online binding/recovery guidance.

## Impact

- **Distro:** shared mail page models, Stalwart JMAP client, online binding services, gateway/client/notifier persistence, passive-server projections, manager commands, and packaged skills under `src/houmao/`.
- **CI:** mocked wire-level JMAP tests, attach/refresh/detach and worker races, channel-isolation regressions, checkpoint recovery, periodic reminder and compaction tests, and multi-component runtime qualification.
- **Utility and docs:** sanitized operational/load qualification tooling in purpose-specific `scripts/qualification/` paths, mailbox setup/limits references, and service deployment guidance. Real credentials and runs remain local and untracked.
- This change leaves offline membership/storage semantics from change 01 intact. It adds no Gmail implementation, cross-channel bridge, global identity collision detector, new plugin framework, or gateway-side mail payload spool.
