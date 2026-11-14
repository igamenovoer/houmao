# Tasks

## 1. Stable Agent Identity Creation

- [x] 1.1 Add one typed identity-creation decision with UUID default, explicit name-hash, and supplied-ID handling; verify unit cases for repeated friendly names, deterministic opt-in hashing, conflicting inputs, and opaque non-UUID IDs.
- [x] 1.2 Pass the resolved ID through brain building, managed prompt headers, runtime start/join, and manager artifact creation; remove generation from serialization/resume/refresh paths and verify each path preserves a stored ID without a new hash/UUID call.
- [x] 1.3 Expose `--agent-id-mode` and corresponding typed creation inputs, repair reusable-template versus existing-agent handling, and update identity/CLI references; verify documented creation/reuse examples and missing-ID validation tests.

## 2. Dual Bindings and Atomic Runtime Authority

- [x] 2.1 Replace the single mailbox union in launch/session models, packaged schemas, configuration, and registry summaries with revisioned offline/online slot envelopes; verify both/one/neither combinations and the full canonical-identity precedence table in unit/schema tests.
- [x] 2.2 Implement the shared interprocess-lock, expected-revision, atomic manifest mutation boundary and route every participating writer through it; verify competing updates, detach/recreate races, interrupted writes, and stale controller persistence with deterministic process tests.
- [x] 2.3 Adapt launch-time Stalwart construction into the online slot and local filesystem configuration into offline binding authority; verify both slots can be configured together without changing owner IDs or silently resetting either backend.
- [x] 2.4 Publish safe dual-mail discovery/status projections and repair local/pair/headless consumers; verify unavailable-channel and projection-failure behavior and update runtime/registry field documentation alongside these changes.

## 3. Registry-Hosted Offline Membership and Ownership

- [x] 3.1 Extend the authoritative filesystem registration index with durable member/agent ownership and atomic address claims, including recoverable mailbox preparation; verify concurrent different-owner claims have one winner and same-owner retry is idempotent.
- [x] 3.2 Remove force/stash takeover and register overwrite confirmation from registration services, managed helpers, generic/project administration, and scoped agent commands; implement serialized explicit release and fresh-registration history isolation and verify no command flag bypasses ownership while external symlink targets and reserved operator rules remain protected.
- [x] 3.3 Separate durable membership from local lifecycle leases, remote presence, tmux probes, and cleanup; verify stopped recipients can receive mail and local cleanup cannot remove remote membership or release addresses.
- [x] 3.4 Enforce selected registry/store association for initialization and generic/project membership mutations while preserving maintenance root selection; verify mismatched roots fail without rewriting configuration and repair preserves registration IDs, member authorization, and attachment authority or rejects missing ownership state; document format-4 backup/rebootstrap, conflicts, release, and recovery without a cluster identifier.

## 4. Registry-Only Remote Service and Client

- [x] 4.1 Add the explicit offline-registry server mode/configuration with only health, membership, mail, and attachment routes; verify its route inventory excludes existing body-control/shutdown surfaces and credential transport configuration rejects unsafe non-loopback plaintext use.
- [x] 4.2 Implement administrative enrollment/release and owner-scoped member credentials with private verifier storage and idempotent enrollment inputs; verify unauthorized inbox/sender selection, lost enrollment responses, explicit credential replacement, and diagnostic redaction.
- [x] 4.3 Add typed remote registry clients for the offline lifecycle set, with finite timeouts and structured outcomes; verify local and remote reads/replies/marks/archive observe the same filesystem authority without opening remote runtime paths.
- [x] 4.4 Add bounded managed attachment upload/download and ownership validation; verify disjoint-host paths, digests/size limits, rejected registry-path selection, and attachment access after message ownership changes.
- [x] 4.5 Write registry-only setup and private credential instructions under the maintained registry/mailbox references; verify setup and reconnect examples against a process/API fixture using separate runtime/store roots.

## 5. Channel-Scoped Mail Facades and Commands

- [x] 5.1 Extract reusable channel-selected mail services/backend contracts and scoped reference handling under the supported package; verify wrong owner/channel/binding rejection, mixed-recipient refusal, and expected-binding checks for fresh send/post before backend side effects.
- [x] 5.2 Add dual summary status and channel-selected gateway lifecycle routes, preserve loopback policy, and update gateway client models; verify both bindings, empty summaries, unsupported operations, stale references, and lifecycle read/answered/archive behavior.
- [x] 5.3 Update passive-server mail/notifier proxies and response/error forwarding for channel and binding scope; verify wrong-channel conflicts are preserved and registry-host offline access remains independent of recipient gateway presence.
- [x] 5.4 Add scoped `mailbox offline status|join|leave` and required mail `--channel` handling; verify single/self targeting, existing-body late activation, conflict rejection without overwrite prompts, and committed-registration/local-publication reconciliation.
- [x] 5.5 Update mail/gateway/CLI reference examples and maintained operator scripts for explicit channel and binding context, scoped self/single resolvers, and current route spellings; verify command help, documented selectors, and representative send/peek/read/reply/archive sequences.

## 6. Per-Channel Notifier and Agent Guidance

- [x] 6.1 Key notifier configuration, scheduling, audit, appendix, and compaction state by owner/channel/binding; verify independent enable/disable/mode changes and periodic reminders for unchanged eligible work on both channels.
- [x] 6.2 Preserve body readiness, pending-input/hook/queue admission and compaction safeguards across simultaneous channel reminders; verify no overlapping terminal work and no compaction reset merely from canonical-address changes.
- [x] 6.3 Update packaged ordinary/notified mailbox routines and prompt rendering to carry explicit channel, expected binding, and exact gateway URL; verify public-entrypoint routing and API fallback when native skill siblings are absent.
- [x] 6.4 Update mailbox workflow and notifier references with dual-mail discovery, archive completion, and no cross-channel fallback; verify skill/prompt tests and documented bounded-round behavior without assuming native skill hot-reload.

## 7. Foundation Integration and Successor Readiness

- [x] 7.1 Run isolated multi-process registry/runtime integration covering two remote members, stopped delivery, service restart, lost join response, release/reassignment, attachment transfers, and both configured launch-time mail slots; record sanitized evidence with no shared-path assumptions.
- [x] 7.2 Run the required unit, lint, type, and affected runtime/integration checks through Pixi, plus `git diff --check` and strict OpenSpec validation; verify gateway plugin event/admission regressions remain unchanged.
- [x] 7.3 Produce an acceptance map from this change's scenarios to tests/evidence and document remaining Stalwart query costs as successor work; verify the foundation does not claim #79/#80 completion and all 02 prerequisites are identifiable.

## Workflow Follow-Up

- Review, verify, and synchronize this change's specs before applying `mail-02-attach-online-mail-and-sync-stalwart`; archive only through the separately requested archive workflow.
- Apply change 02 against the resulting dual-binding/scoped-mail foundation, not against the pre-01 single-mailbox model.
- The approved planning reconciliation replaces obsolete format-3/v1-readability, takeover-locking, released-symlink reuse, and unqualified mail-route/resolver promises before main-spec synchronization; see [acceptance.md](acceptance.md) for the updated scenario inventory and final checks.
