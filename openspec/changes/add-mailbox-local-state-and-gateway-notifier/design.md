## Context

The current filesystem mailbox transport keeps immutable message content on disk and stores mutable mailbox-view state in the shared mailbox-root `index.sqlite`. That works for single-reader flows, but it blurs the line between shared message facts and recipient-local state: `read`, `starred`, `archived`, `deleted`, and unread thread summaries are really mailbox-specific, not shared-root truths.

The gateway already has the right reliability shape for periodic work: a durable per-session root, a queue SQLite database, a read-optimized state artifact, and a serialized worker model. It also already resolves the runtime-owned session manifest from gateway attach metadata, which means the gateway can discover whether the managed session is mailbox-enabled without inventing a second runtime identity channel.

This feature combines those two realities:

- the mailbox transport must stop treating recipient-local state as shared-root state, and
- the gateway can then poll unread mail from the mailbox's local state and schedule a notification turn only when the managed agent is idle.

The guiding constraint is that gateway remains optional. Mailbox truth cannot depend on gateway being present, and gateway MUST NOT become the authority for whether a message is read.

## Goals / Non-Goals

**Goals:**

- Move mailbox-view state that can differ per recipient into a SQLite database stored in each resolved mailbox directory.
- Keep shared mailbox-root state limited to shared catalog concerns such as registrations, canonical messages, recipient associations, attachments, and structural repair inputs.
- Add a gateway-owned mail notifier with enable or disable control and periodic unread-mail polling.
- Reuse the existing gateway queue and single-active-execution model so notification turns obey the same busy and recovery boundaries as other gateway-managed work.
- Make the gateway's on-disk running log an explicit observability surface that operators can tail while the gateway is live.
- Instruct agents to mark messages read only after successful processing through the mailbox-managed helper boundary rather than through gateway-side auto-marking.
- Avoid shared aggregate recipient-status mirrors such as "who has read this thread" caches at the mailbox-root level.

**Non-Goals:**

- Introducing a true email transport or a daemonized mailbox service.
- Making the gateway responsible for automatically marking mail as read.
- Providing a globally materialized "read by all recipients" summary in shared mailbox state.
- General-purpose scheduled jobs beyond the gateway mail notifier.
- Changing canonical message Markdown structure, threading identifiers, or attachment identity rules.

## Decisions

### Decision: Split mailbox storage into shared catalog state and local mailbox-view state

The shared mailbox root remains the authority for shared facts:

- active mailbox registrations,
- canonical message documents,
- sender and recipient associations,
- attachment metadata,
- structural projection catalog data needed for repair.

Each resolved mailbox directory gains its own `mailbox.sqlite`, which becomes the authority for mailbox-view state that can legitimately differ per mailbox:

- `is_read`,
- `is_starred`,
- `is_archived`,
- `is_deleted`,
- thread unread counts and similar mailbox-local summary caches.

This lets sender and recipients carry independent state naturally. A sender can have a sent copy marked read while each recipient maintains its own read or unread and archive status.

Alternatives considered:

- Keep shared-root `mailbox_state` and treat it as authoritative. Rejected because it centralizes state that is conceptually per mailbox and encourages aggregate recipient-status logic.
- Dual-write shared-root aggregate status plus local mailbox state. Rejected because the aggregate mirror introduces synchronization pressure without adding authoritative information.

### Decision: Place the local mailbox database under the resolved mailbox directory

The local mailbox-state database will live at:

```text
<resolved-mailbox-dir>/mailbox.sqlite
```

That path is inside the actual mailbox directory after symlink resolution, not merely inside the shared root entry path. This keeps private mailbox directories self-contained when `mailboxes/<address>` is a symlink to a directory outside the shared root.

Alternatives considered:

- Place local mailbox databases under the shared root keyed by address. Rejected because it separates mailbox-view state from the mailbox directory that owns that view and weakens private-mailbox portability.
- Infer the state path indirectly from `inbox/..` without a fixed filename. Rejected because a stable explicit filename simplifies repair, runtime bindings, and operator inspection.

### Decision: Keep gateway notifier state in gateway-owned persistence, not in mailbox state

Gateway-owned notifier bookkeeping such as:

- whether notifier is enabled,
- polling interval,
- last poll time,
- last notification attempt,
- notification deduplication or cooldown state,
- last notifier error,

belongs to the gateway root rather than to mailbox truth.

The recommended storage model is to extend the existing gateway `queue.sqlite` with notifier-specific tables so restart recovery can reuse the gateway's existing durable SQLite boundary without introducing an extra gateway database file.

Mailbox `mailbox.sqlite` tracks read or unread truth. Gateway notifier state tracks whether this gateway instance has already nudged the agent about unread mail. Those are distinct concepts and should not be collapsed into one flag.

Alternatives considered:

- Store notifier state in mailbox-local SQLite. Rejected because notifier policy is gateway behavior, and gateway is optional.
- Create a second gateway-owned SQLite file just for notifier state. Rejected because the gateway already has a durable SQLite boundary and separate files add extra artifact and locking complexity.

### Decision: Notification turns enter the existing gateway execution path as internal requests

The notifier poll loop will not send terminal input directly. Instead, when it finds unread mail and the gateway is idle, it inserts an internal non-public request into the existing gateway queue. The gateway worker then executes that request through the same serialized path used for other terminal-mutating work.

This preserves:

- single active execution semantics,
- queue durability,
- event-log visibility,
- restart behavior,
- admission-state checks.

Public request kinds remain `submit_prompt` and `interrupt`. The notifier-specific request kind is an internal stored request type, not part of the public HTTP creation contract.

Alternatives considered:

- Let the poller inject terminal input directly. Rejected because it bypasses the queue, races concurrent operator or gateway work, and makes recovery harder to reason about.
- Expose notifier-triggered prompt submission as another public request kind. Rejected because this is system-owned gateway behavior, not a public caller operation.

### Decision: Expose notifier control through idempotent gateway endpoints

The gateway will expose dedicated notifier control and status endpoints:

- `PUT /v1/mail-notifier`
- `GET /v1/mail-notifier`
- `DELETE /v1/mail-notifier`

`PUT` enables or reconfigures notifier state, `DELETE` disables it, and `GET` reports current configuration and runtime status. This keeps notifier control explicit and idempotent without overloading `GET /v1/status`.

The base `GET /v1/status` contract can remain focused on gateway and upstream-agent state, while notifier-specific details live behind the notifier-specific endpoint.

Alternatives considered:

- `POST /enable` and `POST /disable` endpoints. Rejected because repeated calls are less naturally idempotent and configuration updates become clumsier.
- Folding notifier status into `GET /v1/status` only. Rejected because notifier configuration and operational counters are a separate concern from core gateway health and admission.

### Decision: Keep a tail-friendly gateway running log on disk as an explicit operator contract

The gateway already has a disk log path under the gateway root. This change makes that running log an explicit operator-facing contract instead of an incidental child-process stdout sink.

`<session-root>/gateway/logs/gateway.log` will remain append-only and line-oriented so operators can watch it safely with tools such as `tail -f`.

The gateway will log at minimum:

- gateway process start and stop,
- notifier enable, disable, and configuration changes,
- poll-cycle outcomes such as unread detected, no unread mail, busy deferral, mailbox-disabled rejection, and enqueue success,
- internal notification request execution start and finish,
- explicit notifier and mailbox polling errors.

The running log is for human observability. Durable request history and machine-readable recovery state remain in structured artifacts such as `queue.sqlite`, `events.jsonl`, and `state.json`.

To keep short poll intervals usable, repetitive skip messages such as "agent still busy; retry next cycle" should be rate-limited or coalesced rather than emitted on every single poll forever.

Alternatives considered:

- Treat the current stdout redirection as sufficient and leave the running log undocumented. Rejected because operators need a stable tail-watch surface when debugging notifier behavior.
- Put all observability into `events.jsonl` only. Rejected because the event log is durable machine-oriented state, while operators still need a readable live log stream.

### Decision: Busy means no queued or running gateway work and open admission

The poll loop treats the managed agent as unavailable for notification when any of these conditions hold:

- `request_admission != open`,
- `active_execution == running`,
- `queue_depth > 0`.

When any of those states apply, the poll loop records a busy skip and waits for the next interval rather than enqueueing a stale notification that will sit behind unrelated work.

Alternatives considered:

- Allow notifier requests to queue behind existing work. Rejected because notification freshness matters and queued reminders can become noisy or misleading.
- Treat only `active_execution == running` as busy. Rejected because accepted-but-pending work still means the session is already committed to gateway-managed activity.

### Decision: Agents mark mail read explicitly after processing

The notifier prompt is only a nudge. It tells the agent that unread mail exists and includes compact metadata such as subject lines and message identifiers. The agent then uses the runtime-owned mailbox skill and managed helper scripts to inspect and process mail.

Only after successful processing does the agent mark a message read by invoking the mailbox-state mutation helper. The gateway never marks read merely because it detected unread mail or because it successfully submitted a reminder prompt.

Alternatives considered:

- Gateway marks mail read as soon as notification is accepted. Rejected because prompt acceptance is not the same as message processing, and mailbox semantics must remain valid without gateway.
- Gateway marks mail read after prompt completion. Rejected because prompt completion still does not prove the agent actually processed every notified message correctly.

### Decision: Migrate existing shared-root mailbox state into local mailbox databases

The mailbox transport will migrate prior shared-root recipient-state rows into each mailbox's `mailbox.sqlite` when it encounters an existing mailbox root created under the old model.

Migration will:

1. create `mailbox.sqlite` for each discovered active mailbox,
2. copy per-mailbox state from shared-root `mailbox_state` into the corresponding local database when available,
3. rebuild local thread summaries from local message-state rows,
4. stop treating shared-root recipient-state tables as authoritative afterward.

The shared-root repair path remains able to rebuild structural catalog data from canonical messages. Local mailbox repair remains able to initialize deterministic local state defaults when prior local state is absent.

Alternatives considered:

- Hard fail on old mailbox roots and require manual reset. Rejected because existing dev mailboxes should be upgradeable without discarding message history.
- Keep reading old shared-root state forever as a fallback. Rejected because it preserves ambiguous dual authority.

### Decision: Publish explicit env bindings for the resolved mailbox directory and local mailbox SQLite path

Mailbox-enabled sessions will continue to receive shared-root bindings such as the mailbox root and shared catalog SQLite path, but will also receive explicit local-mailbox bindings for:

- the resolved mailbox directory,
- the local mailbox SQLite path.

To stay aligned with the current runtime binding surface, the change will preserve:

- `AGENTSYS_MAILBOX_FS_ROOT` as the shared mailbox root binding,
- `AGENTSYS_MAILBOX_FS_SQLITE_PATH` as the shared-root catalog SQLite binding,
- `AGENTSYS_MAILBOX_FS_INBOX_DIR` as the resolved inbox binding.

The change will add explicit local-mailbox bindings:

- `AGENTSYS_MAILBOX_FS_MAILBOX_DIR` for the resolved mailbox directory,
- `AGENTSYS_MAILBOX_FS_LOCAL_SQLITE_PATH` for the mailbox-local `mailbox.sqlite` path.

This lets agents and future tooling use stable runtime-managed bindings instead of reconstructing local mailbox paths from the inbox path heuristically.

The projected mailbox skill and shared mailbox helper scripts remain the mutation boundary for any step that touches shared-root `index.sqlite`, mailbox-local `mailbox.sqlite`, or mailbox locks. Moving recipient-local state into local SQLite does not authorize agents to start hand-writing raw local SQLite mutations directly.

Alternatives considered:

- Infer local mailbox state from `AGENTSYS_MAILBOX_FS_INBOX_DIR`. Rejected because explicit runtime bindings are clearer and more robust when the mailbox structure evolves.
- Reinterpret `AGENTSYS_MAILBOX_FS_SQLITE_PATH` as the mailbox-local database. Rejected because current code and skill materials already use that name for the shared-root `index.sqlite`, and overloading it would create avoidable ambiguity.

## Risks / Trade-offs

- [Migration complexity] -> Mailbox roots created under the old shared-state model need deterministic upgrade logic and regression coverage for mixed historical state.
- [Split write path] -> Delivery and mailbox-state mutation now touch shared catalog state plus one or more local mailbox databases; shared address locks and bounded transactional phases must remain strict.
- [Notifier duplication risk] -> Without gateway-owned deduplication state, idle polling can spam the agent; keeping notifier history in gateway-owned persistence limits repeats without redefining mailbox truth.
- [Log volume from frequent polling] -> Busy-deferral and empty-poll paths should use rate-limited or coalesced log emission so `gateway.log` stays tail-friendly under short notifier intervals.
- [Busy-session deferral] -> A long-running active session may postpone notifications for a while; this is intentional to preserve operator and gateway work ordering, and the next poll retries when the session becomes idle.
- [Cross-mailbox aggregate queries become fan-out work] -> Questions like "which recipients have read this message?" now require checking each recipient mailbox individually. This is an accepted trade-off to avoid authoritative aggregate mirrors and sync drift.

## Migration Plan

1. Add the per-mailbox `mailbox.sqlite` schema and explicit runtime bindings for resolved mailbox directory plus local SQLite path.
2. Update mailbox bootstrap, delivery, state mutation, and repair flows to create and maintain local mailbox state while preserving shared-root catalog behavior.
3. Implement migration from legacy shared-root `mailbox_state` and summary rows into per-mailbox local databases.
4. Update the projected mailbox system skill and managed helper expectations so agents use the local mailbox-state contract and explicit mark-read-after-processing guidance.
5. Extend gateway persistence and HTTP surface with notifier control and status, then add the poller plus internal notification request execution path.
6. Make `gateway.log` an explicit tail-friendly operator log and add notifier/lifecycle log coverage with rate-limited busy-retry logging.
7. Update gateway and mailbox docs and add migration-focused tests for old mailbox roots, local-state repair, notifier behavior, and running-log observability.

Rollback approach:

- Before the gateway notifier is enabled, mailbox local-state migration can be validated independently.
- If notifier behavior is unstable, disable it through the gateway control endpoint without invalidating mailbox local-state correctness.
- Legacy shared-root recipient-state tables may remain readable during the migration window as source material, but the implementation should stop treating them as authoritative after migration succeeds.

## Open Questions

- Should notifier deduplication default to "notify once until read" or allow an explicit cooldown-based renotification policy in the first implementation? The current recommendation is "once until read" to avoid agent spam.
- Should gateway notifier runtime counters also be surfaced as an optional nested object in `GET /v1/status`, or should they remain available only through the dedicated notifier endpoint? The current recommendation is to keep them on the dedicated endpoint first.
- Should repeated "no unread mail" poll outcomes be logged at all, or only summarized periodically, to avoid low-value log churn under short intervals? The current recommendation is to log state transitions and periodic summaries rather than every identical empty poll forever.
