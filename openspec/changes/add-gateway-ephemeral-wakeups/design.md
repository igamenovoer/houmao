## Context

The gateway already has two useful timing-related patterns:

- a durable serialized worker for accepted terminal-mutating work,
- a timer loop for gateway-owned mailbox notifier behavior.

That existing notifier path is not a good fit for direct self-wakeup. It depends on mailbox capability, it translates reminders through unread-mail polling, and it persists internal prompt requests durably. The proposed wakeup feature has different requirements:

- it must be available without mailbox support,
- it must accept a predefined prompt directly from the caller,
- it must support both one-off and repeating timers,
- it must remain fully in memory,
- pending wakeups must be lost when the gateway stops or restarts,
- canceling a repeating wakeup must stop future occurrences.

The current gateway contract also already constrains public request kinds to `submit_prompt` and `interrupt`, so wakeup support should not appear as another public terminal-mutating request kind.

## Goals / Non-Goals

**Goals:**
- Add direct gateway wakeup registration routes for one-off and repeating wakeups.
- Keep wakeup state entirely inside the live gateway process with no restart recovery.
- Preserve the existing public request-kind contract of `submit_prompt` and `interrupt`.
- Ensure due wakeups only submit prompts when the gateway can do so safely and without preempting already accepted public work.
- Support explicit cancellation of scheduled wakeups and future repetitions.

**Non-Goals:**
- Durable wakeup persistence or replay across gateway restart.
- Cron-style expressions, calendar scheduling, or multi-step workflow scheduling.
- A new persistent wakeup table or recovery artifact under the gateway root.
- Hard recall of a prompt that has already started executing against the managed agent.
- Pair-owned `houmao-server` projection routes in this change.

## Decisions

### Decision: Wakeups use dedicated HTTP routes instead of extending `POST /v1/requests`

The gateway will expose dedicated wakeup registration, listing, inspection, and cancellation routes rather than adding scheduling fields to `POST /v1/requests` or introducing a new public request kind.

Why this approach:
- it preserves the current public terminal-mutating request-kind set,
- it keeps future-timer registration distinct from immediate prompt submission,
- it avoids confusing queue depth with not-yet-due wakeups.

Alternatives considered:
- adding `schedule_at` to `submit_prompt`.
  Rejected because future-due items would blur immediate queue semantics and encourage callers to treat durable request storage as a scheduler.
- adding a public request kind such as `wakeup_prompt`.
  Rejected because wakeups are registration behavior, not an immediately executable terminal-mutating request kind.

### Decision: Wakeup jobs are process-local in-memory state

Registered wakeup jobs will live only in the active `GatewayService` process. The gateway will keep an in-memory registry plus a scheduler-owned next-due index and will drop that state on shutdown or restart.

Why this approach:
- it matches the selected product requirement exactly,
- it avoids inventing persistence, migration, and replay rules for reminder-like state,
- it makes restart behavior simple and explicit.

Alternatives considered:
- storing wakeups in `queue.sqlite`.
  Rejected because restart recovery would preserve wakeups, which violates the desired ephemeral contract.
- storing only the schedule in memory but converting due wakeups into durable internal queue records before execution.
  Rejected because a due-but-not-yet-run wakeup would then survive restart indirectly through durable queue recovery.

### Decision: Due wakeups use a shared execution helper but do not become durable queued requests

When a wakeup becomes due, the gateway will attempt to execute it through the same internal prompt-submission helper used by other gateway prompt paths, but it will not first persist a durable `gateway_requests` row.

Why this approach:
- it preserves one execution path to the adapter,
- it satisfies the non-durable wakeup requirement,
- it avoids distorting queue-depth semantics with pending timer jobs.

Alternatives considered:
- enqueueing wakeups into the durable internal request path used by the mail notifier.
  Rejected because that path intentionally survives restart and is therefore incompatible with ephemeral wakeups.
- letting the wakeup scheduler inject directly into the provider adapter with no shared execution helper.
  Rejected because it would create a second uncontrolled execution path and make concurrency harder to reason about.

### Decision: Public queued work keeps priority over due wakeups

Due wakeups will only submit when request admission is open, no gateway execution is active, and the durable public queue depth is zero. If the gateway is busy, the wakeup remains pending in memory until the next safe opportunity.

Why this approach:
- it keeps accepted public work authoritative,
- it prevents reminder prompts from jumping ahead of operator or caller-submitted work,
- it aligns wakeups with the current “run when idle” behavior already used by the notifier conceptually.

Alternatives considered:
- reserving a slot for due wakeups as soon as their timer fires.
  Rejected because that would let reminders interfere with normal prompt traffic.
- treating due wakeups as durable queued work behind public requests.
  Rejected because durable queue insertion would violate the selected restart-loss behavior.

### Decision: Repeating wakeups use anchored cadence with no catch-up burst

Repeating wakeups will keep one repeating cadence and at most one pending due occurrence. If the gateway is busy through multiple intervals, the gateway will not backfill multiple immediate prompt deliveries when it becomes idle again.

Why this approach:
- it prevents reminder floods after a long busy period,
- it keeps repeating wakeups understandable as periodic nudges rather than backlog generation,
- it avoids turning repeating wakeups into an implicit queue generator.

Alternatives considered:
- fixed-delay repetition from the previous successful delivery.
  Rejected because repeated busy periods would cause unbounded cadence drift.
- backfilling every missed interval.
  Rejected because it would create noisy bursts and undermine the “remind me periodically” use case.

### Decision: Cancellation stops scheduled or future occurrences, not an already executing prompt

Deleting a wakeup job will remove it from the in-memory scheduler immediately if it has not yet begun execution. For a repeating wakeup, deletion also prevents future repetitions. If a prompt from that wakeup is already executing, deletion will not recall it; interruption remains a separate control action.

Why this approach:
- it gives callers a clear and implementable cancellation boundary,
- it avoids pretending the system can retract already-delivered terminal input,
- it keeps wakeup cancellation semantics aligned with other gateway execution semantics.

Alternatives considered:
- promising cancellation of an already executing wakeup prompt.
  Rejected because terminal injection is not safely reversible once execution starts.

## Risks / Trade-offs

- [Wakeups disappear on restart or crash] → Document the live-only contract explicitly in the API and spec, and keep inspection routes focused on current-process state only.
- [A long busy period can delay reminders significantly] → Treat wakeups as low-priority idle-time nudges and prevent catch-up bursts when the gateway becomes free again.
- [Cancellation races near execution start] → Define cancellation as authoritative only until execution begins; use interrupt separately for already executing work.
- [The wakeup path diverges from the mail-notifier internal enqueue model] → Keep a shared prompt-execution helper even though persistence behavior differs, so the adapter and concurrency rules stay centralized.

## Migration Plan

1. Add gateway HTTP models and client support for wakeup registration, listing, inspection, and cancellation.
2. Add an in-memory wakeup registry and scheduler loop to the live gateway runtime.
3. Refactor gateway prompt execution so durable queued requests and ephemeral wakeups can share one execution helper without sharing persistence.
4. Add gateway unit and integration coverage for one-off, repeat, cancellation, busy deferral, and restart-loss behavior.
5. Update gateway docs and any operator-facing references that describe the live gateway HTTP surface.

Rollback is straightforward: remove the wakeup routes and in-memory scheduler, leaving the existing durable request and notifier behavior unchanged.

## Open Questions

- None. This change intentionally stays narrow: direct gateway wakeups only, live-memory only, no server projection, and no durable recovery.
