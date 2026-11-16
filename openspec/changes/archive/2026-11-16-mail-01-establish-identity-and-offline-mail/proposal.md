# Proposal

## Why

Houmao currently derives default agent IDs from names and selects one mailbox transport per session. Stable global identity, simultaneous offline and online mail, and agents on different hosts require a shared foundation before live online attachment and efficient Stalwart synchronization can be implemented coherently.

This is change **01 of 02**. Implement and synchronize its specs before [mail-02-attach-online-mail-and-sync-stalwart](../2026-11-16-mail-02-attach-online-mail-and-sync-stalwart/proposal.md). This change establishes the prerequisite contracts; it does not close GitHub #79 or #80.

## What Changes

- **BREAKING:** Generate UUIDs by default when creating agents. Retain explicit name-hash generation and supplied IDs. Persist identity once; names, mail addresses, sessions, hosts, and process generations do not redefine it. Identical IDs mean the same agent; accidental ID collisions are outside detection guarantees.
- **BREAKING:** Replace the single mailbox union with independent optional `offline` and `online` bindings. Derive the canonical mail identity from online mail first, then offline mail, independently of connection health.
- Establish one registry host as the membership and filesystem mail authority for an offline cluster. Remote agents use a scoped Houmao API. Registry selection supplies the context; introduce no `cluster_id` or substitute cluster identifier.
- Atomically reject offline address claims by a different agent. Preserve idempotent rejoin, durable membership while bodies are stopped, explicit release, and history isolation on address reassignment. Remove force/stash takeover from join flows.
- **BREAKING:** Use mailbox format 4 and reject unsupported earlier roots and canonical envelopes with explicit backup/rebootstrap guidance. Preserve ownership, registration IDs, member authorization, and attachment authority during repair; do not reconstruct owners from mailbox paths.
- **BREAKING:** Require explicit mail channels in gateway, passive-server, manager, and skill operations. Scope message references to owner and binding. Offline and online delivery remain separate, without forwarding, fallback, or address translation.
- Add revision-checked atomic binding persistence, per-channel notifier configuration, and secret-free discovery projections. Preserve periodic reminders, archive completion, readiness gates, and one-shot compaction behavior.
- Adapt existing launch-time Stalwart configuration to the online slot. Live externally provisioned attachment, metadata-only bounded JMAP access, and incremental sync belong to change 02.

## Capabilities

### New Capabilities

- `agent-mailbox-bindings`: Dual optional bindings, canonical mail identity, scoped references, revision ownership, and backend capabilities.
- `offline-mail-registry`: Durable registry-host membership, unique offline addresses, authenticated remote mailbox access, and filesystem storage authority.

### Modified Capabilities

- `agent-identity`: Immutable global agent IDs, UUID defaults, optional name-hash generation, and creation-only selection.
- `agent-discovery-registry`: Separate durable mail membership from runtime presence and publish dual-mail identity summaries.
- `agent-mailbox-protocol`: Stable agent owners, explicit isolated mail channels, and current-format envelope validation.
- `agent-mailbox-registration-lifecycle`: Reject address takeover, separate release from fresh registration, and serialize delivery with explicit ownership release.
- `managed-agent-mailbox-registration`: Scoped local/remote offline registration without body restart.
- `agent-gateway`: Channel-specific mail routes and dual-binding status.
- `agent-gateway-mail-notifier`: Independent channel controls and periodic reminder admission.
- `agent-mailbox-system-skills`: Discover both bindings and operate on an explicit channel.
- `passive-server-gateway-proxy`: Preserve channel and binding scope across mailbox proxies.
- `houmao-srv-ctrl-native-cli`: Identity-generation options and scoped channel-aware mail/registration commands.
- `houmao-mgr-mailbox-cli`: Administrative registration obeys exclusive ownership, initialization verifies registry/store association, and repair preserves membership authority.
- `houmao-mgr-project-mailbox-cli`: Project wrappers preserve the same conflict rejection and selected registry/store authority.

## Impact

- **Distro:** identity creation, launch/session boundary models and schemas, registry storage/discovery, mailbox services and filesystem ownership, gateway/client/notifier, passive-server API/config/client, and scoped manager commands under `src/houmao/`.
- **CI:** identity, concurrent registration, binding persistence, channel isolation, remote mailbox, notifier, and runtime integration tests under `tests/unit/`, `tests/integration/`, and `tests/workflow/` as appropriate.
- **Docs and skills:** identity and registry references, mailbox/CLI workflows, and packaged mailbox routines. Repair maintained callers around the new contracts; do not introduce single-mailbox compatibility shims or implicit name-derived recovery.
- Use existing Python, SQLite, FastAPI, and HTTP infrastructure. No new plugin framework or public email-provider implementation is required. Remote mail participation grants no body lifecycle authority. Gateway plugin event-dispatch contracts remain independent.
