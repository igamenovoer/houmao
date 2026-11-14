# Tasks

## 1. Verify the Ordered Foundation and Mail Capability Gate

- [ ] 1.1 Verify `cccc-01-add-owner-bound-chat-plugin` is implemented, qualified, and synchronized into main specs; confirm its installed wheel, compatible provider source, normal Actor grants, immediate dispatch, and no-replay evidence before starting Mail work.
- [ ] 1.2 Extend the provider/plugin capability inventory with the required Mail operation, bound, cursor, and read-receipt features; verify a chat-only provider keeps chat working while rejecting unqualified consuming-read support.
- [ ] 1.3 Document the Mail extension's provider compatibility requirements and explicit separation from offline/online email; verify examples select the CCCC plugin binding rather than adding another manifest email slot.

## 2. Implement Bounded Native Deferred Operations

- [ ] 2.1 Add owner-scoped native Mail send/reply to the compatible provider with existing operation-ID reconciliation; verify forced `mail` mode, native event/reply IDs, Actor recipient validation, and no direct prompt or email-side mutation.
- [ ] 2.2 Add Actor-private pending metadata, bounded non-consuming peek, and authoritative cursor inspection; verify repeated status/peek/history create no consuming read fact and capped/unknown counts remain explicit.
- [ ] 2.3 Select complete leading read batches under count and serialized-byte limits before any cursor commit; verify interleaved direct traffic is excluded, later Mail remains pending, and an oversized first item fails without skipping or consuming it.
- [ ] 2.4 Land provider tests and protocol documentation for explicit Mail modes, recipient scope, inspection semantics, and advertised content limits; verify all normal operations work with only the existing Actor grant.

## 3. Add Authoritative Read Operation Decisions and Recovery

- [ ] 3.1 Extend the provider's serialized read mutation with an expected-cursor precondition and Actor-generation/operation-scoped request fingerprint; verify concurrent distinct reads from one cursor produce one consumption and one conflict.
- [ ] 3.2 Commit read operation identity, before/after boundary, exact bounded event IDs, and consumed/empty outcome with the native journal/read fact; verify matching reuse returns the original receipt and conflicting reuse never consumes another batch.
- [ ] 3.3 Persist empty-operation decisions and safe receipt retention/index behavior for the Actor registration; verify repeating an empty read after new arrival leaves that Mail pending and archived/expired decisions cannot become fresh reads.
- [ ] 3.4 Add normal-Actor non-consuming read-receipt lookup and crash recovery across pending-marker, read-fact, and cursor-publication boundaries; verify restart preserves the original receipt and effective cursor without replaying consumed Mail.
- [ ] 3.5 Document the read request/receipt contract and reconciliation sequence, including unknown outcomes and repeated-operation responses; verify tests exercise the actual provider journal rather than a separately written post-read receipt cache.

## 4. Expose Mail Through the Installed Plugin and CLI

- [ ] 4.1 Add strict Mail request/result models and scoped cursor/read-operation handles using change 01's reference authority; verify cross-owner, replaced binding, Actor-generation, malformed, and email-channel references fail before provider access.
- [ ] 4.2 Add namespaced Mail send/reply/peek/cursor/read/receipt routes and maintained safe status; verify expected binding selection, `backend=cccc-mail`, finite limits, unchanged native cursor for inspection, and explicit unsupported email-style operations.
- [ ] 4.3 Implement one consuming provider call per explicit read with automatic mutation retries disabled and response-loss uncertainty surfaced; verify receipt lookup plus bounded exact history recovery leaves the following batch untouched.
- [ ] 4.4 Extend the thin CLI with Mail operations and readable consumed/empty/already-completed/uncertain results; verify it never resolves provider credentials, silently changes operation IDs, or hides the caller's reconciliation identity.
- [ ] 4.5 Add wire-level unit tests and agent-facing API/CLI documentation for count/byte preconditions, empty-operation reuse, cursor conflict, reply-without-read, receipt recovery, and unsupported archive/attachment behavior; verify documented commands against the built optional wheel.

## 5. Preserve Deferred Notices and Email Coexistence

- [ ] 5.1 Connect qualified provider content-free Mail notices to change 01's immediate handoff path; verify busy/unavailable bodies refuse without local queueing, Mail consumption, direct message-body delivery, or replay on idle/reconnect.
- [ ] 5.2 Preserve the native pending-batch notice policy and independent offline/online periodic reminder and compaction state; verify repeated eligible email cycles still remind while CCCC notice/cursor changes do not reset email state.
- [ ] 5.3 Add isolated coexistence tests and documentation covering simultaneous offline email, online Stalwart email, and CCCC Mail, including a selected Stalwart fault endpoint; verify explicit CCCC use works without fallback, mirroring, address translation, or canonical-identity changes.

## 6. Qualify Actual Provider and Installed-Package Behavior

- [ ] 6.1 Extend actual-provider tests under `tests/integration/cccc/` using two normal Actor grants and independent gateways; verify send/read/reply ancestry, non-consuming inspection, ordered cursor advancement, stale cursor conflicts, and same-binding gateway restart continuity.
- [ ] 6.2 Add response-loss and provider-crash qualification around read-fact/cursor persistence, concurrent native/gateway reads, receipt replay, generation replacement, lease-expiry waiting, and operator takeover; verify original read outcomes are recoverable without consuming another batch or retrying an unsettled notice.
- [ ] 6.3 Upgrade independent wheels in a clean external environment and verify Mail routes/CLI, credential refresh, stale-reference rejection, maintained chat behavior, and unchanged body PID/conversation without source imports.
- [ ] 6.4 Update the pinned provider manifest/patch series, native deployment example, integration reference, qualification driver, and complete scenario acceptance map; verify a clean documented setup reproduces actual Mail protocol evidence with private credentials and precise executed/unexecuted scope.
- [ ] 6.5 Run the required small Mail smoke with two real managed coding agents using the supported fixture launcher, installed Houmao/plugin distributions, distinct gateway/Actor bindings, and actual compatible CCCC; verify agent-authored deferred send, explicit batch read/cursor advancement, and Mail reply ancestry, record secret-safe client/profile/result evidence, and leave #78 acceptance pending if prerequisites or execution fail.
- [ ] 6.6 Run `pixi run format`, `pixi run lint`, `pixi run typecheck`, `pixi run test`, optional-package checks, affected CCCC/mail integration and provider tests, distribution validation, and strict OpenSpec validation; verify issue #78 acceptance includes the passed two-real-agent Mail smoke without weakening chat or email contracts.

## Workflow Follow-Up

- Review qualification evidence and the complete acceptance map before synchronizing and archiving this change.
- Update the roadmap and close issue #78 only after implementation, deterministic/provider qualification, and the required two-real-agent Mail smoke pass; proposal creation does not establish completion.
