# Tasks

## 1. Foundation Gate and Shared Page Contract

- [ ] 1.1 Confirm `mail-01-establish-identity-and-offline-mail` is implemented and synchronized into main specs; verify UUID/name-hash creation, dual slot revisions, expected-binding checks, registry-host offline access, and per-channel notifier tests before changing online behavior.
- [ ] 1.2 Add strict finite metadata-page request/response models with scoped cursors, page counts, continuation, and completeness fields; verify schema cases for both channels, oversized limits, absent limits, wrong binding/filter scope, and rejected `include_body` input.
- [ ] 1.3 Adapt offline list pagination to the shared page model without adding online sync state; verify local/remote offline continuation against the existing authoritative indexes and update shared mail-page contract documentation.

## 2. Bounded Stalwart Client Operations

- [ ] 2.1 Separate session-discovery and method-call endpoints, pin account/sending identity, and reuse connection-scoped discovery/role maps; verify wire tests for non-primary requested identities, ambiguous accounts, login/address differences, advertised API paths, missing roles, and no per-message mailbox enumeration.
- [ ] 2.2 Implement server-side mailbox/read/answered/archive/time filtering before bounded query pagination; verify old unread mail behind newer read mail, timestamp boundaries, multiple mailbox memberships, unsupported filters, and provider result caps with mocked JMAP.
- [ ] 2.3 Implement metadata-only batch gets and state-validated opaque continuation; verify request properties exclude body values/text bodies/attachment bytes and continued pages reject account/filter/query-state drift instead of silently combining results.
- [ ] 2.4 Preserve explicit peek/read/send/reply/mark/move/archive behavior and expose content completeness/limits; verify truncated body values are visible, peek is non-mutating, reply updates parent flags, archive closes inbox work, and uncertain sends are not retried automatically.
- [ ] 2.5 Document supported filters, discovery URLs, page/count meaning, cursor errors, and body limits in the Stalwart/mailbox references; verify examples against the mocked wire contract and remove unqualified/full-body list guidance.

## 3. Incremental Observation and Recovery

- [ ] 3.1 Add account/binding/view-scoped mail-sync persistence to gateway-owned SQLite with atomic metadata/checkpoint commits; verify restart, commit failure, idempotent replay, and identity separation across overlapping provider message IDs.
- [ ] 3.2 Implement bootstrap/rebase with an email-state boundary captured before the bounded eligible query, then bounded `Email/changes` catch-up; verify interleaved arrivals, intermediate states, partial fetch failure, `notFound`, and no advancement from an unrelated newer get-state.
- [ ] 3.3 Add compatible query-change handling and bounded recovery for stale state, oversized query deltas, missing capabilities, and cache loss; verify query deltas are not paged using email-change semantics and recovery never scans all retained bodies/history.
- [ ] 3.4 Enforce request/item/time budgets, cached-window bounds, backoff, and honest idle/catch-up/rebase/degraded status; verify limits yield resumable progress, samples are not presented as exact totals, and eligible work remains discoverable during catch-up.
- [ ] 3.5 Document checkpoint scope, query-state distinction, recovery phases, cache disposal, and operating budgets; verify a reconnect/stale-state example matches the implemented status and wire tests.

## 4. Live Online Binding Lifecycle

- [ ] 4.1 Add candidate attachment validation and private credential snapshots without provisioning calls or required management configuration; verify bad credentials, endpoint timeout, address mismatch, ambiguous accounts, and secret-safe errors leave previous bindings unchanged.
- [ ] 4.2 Implement owner/revision-checked attach and explicit replacement using the foundation mutation service; verify initial attachment, dual-mail preservation, canonical identity changes, concurrent controls, and stale new-send preconditions without body PID/conversation replacement.
- [ ] 4.3 Implement same-account credential refresh and connection reconnect with revision/epoch fencing; verify source-file replacement preserves account checkpoints, different-account refresh fails, and no hub-supplied provider password is rotated.
- [ ] 4.4 Implement detach and bounded retirement of old clients/workers/requests, including pre-commit failure handling and private owned-copy cleanup; verify late poll completion cannot publish or wake another binding and externally owned files/provider mail remain intact.
- [ ] 4.5 Handle already-started mutation uncertainty during retirement without automatic resend; verify each returned outcome remains pinned to the old binding and a failed retirement does not report false activation.
- [ ] 4.6 Document the online operator lifecycle and gateway-companion prerequisite using supported commands and protected references; verify attachment/reconnect/detach examples and the distinction between configured mail and active notifier service.

## 5. Bounded Periodic Notifier Integration

- [ ] 5.1 Replace unbounded online inbox polling with bounded synchronized views outside the terminal lock; verify request budgets, busy-body preservation, no body retrieval, and continued periodic reminders for unchanged any-inbox/unread-only work.
- [ ] 5.2 Persist cycle admission atomically with the internal reminder request and fence pending work to its origin binding/revision; verify same-cycle reconnect retries do not duplicate pending wakeups and replacement cancels unstarted old reminders.
- [ ] 5.3 Preserve compaction eligibility independently of metadata-window eviction, credential refresh, and checkpoint rebase; verify bounded eligibility revalidation and retain #37 compaction-loop and #51 prompt-readiness regressions.
- [ ] 5.4 Update notifier status/audit documentation and tests to distinguish observed sync progress, bounded summaries, readiness skips, and due reminder cycles; verify no permanent message/digest suppression is introduced.

## 6. Supported CLI, API, Proxy, and Skill Consumers

- [ ] 6.1 Expose loopback/authorized online binding control routes and typed gateway clients, with safe snapshot reads; verify every mutation's owner/revision handling and registry-only/member credentials cannot reach online management.
- [ ] 6.2 Add scoped `mailbox online status|attach|refresh|reconnect|detach`, finite `mail list --limit/--cursor`, and passive-server projections; verify exact forwarding of scope, structured conflicts/cursor errors, committed-but-unpublished outcomes, and removed `--include-body` rejection.
- [ ] 6.3 Update packaged ordinary/notifier mailbox routines for metadata pages, round budgets, expected binding IDs, explicit content reads, and stale-round interruption; verify public-entrypoint/API fallback paths without ambient credential discovery or channel fallback.
- [ ] 6.4 Update Stalwart setup, mailbox/CLI/gateway references, and developer fixture guidance with normal-account attachment and protected credentials; verify documented examples use maintained surfaces and contain no real keys or credential-bearing tracked artifacts.

## 7. Live Qualification and Acceptance

- [ ] 7.1 Run deterministic runtime/API integration for attach on a disabled running body, invalid credentials, endpoint failure, refresh/reconnect/detach, cross-channel isolation, account replacement races, gateway restart, and successful read/send/reply/archive; verify stable body PID and conversation markers.
- [ ] 7.2 Qualify the running Stalwart release with an explicitly selected private normal-account credential and no management credential for attachment; exercise bounded metadata, explicit content, changes, refresh, restart recovery, and detach, recording sanitized evidence and actual service version.
- [ ] 7.3 Add purpose-specific qualification tooling and a documented load plan for 100 agents/millions of retained messages; verify a representative small workload records requests, bytes, latency, memory, backlog recovery, and reminder counts while clearly separating measured scale from unexecuted targets.
- [ ] 7.4 Run required Pixi unit/lint/type checks and affected runtime/integration suites, `git diff --check`, and strict OpenSpec validation; verify offline registry and generic gateway plugin regressions still pass.
- [ ] 7.5 Produce an acceptance map for #79/#80 and these spec scenarios, including periodic-reminder clarification, limitations, and tested scale; verify every criterion links to a test or explicitly scoped live/load-plan artifact before declaring implementation complete.

## Workflow Follow-Up

- Review and verify the completed implementation, then synchronize/archive only through the separately requested workflow.
- Review #79/#80 closure against the acceptance map after implementation; planning completion alone does not close either issue.
