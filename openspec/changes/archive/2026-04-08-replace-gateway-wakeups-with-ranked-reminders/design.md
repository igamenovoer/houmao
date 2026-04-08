## Context

The current gateway wakeup feature is implemented as a live in-memory set of independent timer jobs on the gateway sidecar. Each wakeup owns one prompt, one due-time configuration, and optional repeating cadence, and the scheduler simply finds the earliest due job that can run when the gateway is idle.

That model is no longer sufficient. The target behavior is a live reminder set with explicit operator-visible metadata and arbitration rules: each reminder has a title, arbitrary prompt string, signed ranking value, pause state, and due-time behavior; the reminder with the smallest ranking value is the only effective reminder; and a paused effective reminder still blocks all lower-priority reminders. This change is cross-cutting because it replaces a live HTTP route family, the gateway runtime's in-memory scheduling model, the gateway client models, the packaged gateway skill guidance, and the CLI reference docs that currently describe `/v1/wakeups`.

The repo's current development posture allows direct breaking changes, so this design assumes a clean replacement rather than a compatibility alias. The existing non-durable boundary also stays in force: reminders remain live gateway process state and are lost when the gateway stops or restarts.

## Goals / Non-Goals

**Goals:**

- Replace `/v1/wakeups` with `/v1/reminders` as the supported direct live gateway reminder API.
- Support creating more than one reminder in one request.
- Add reminder metadata needed by the new product behavior: `title`, `prompt`, `ranking`, and `paused`.
- Preserve time-based scheduling support, including one-off and repeating reminders, so the refactor does not unnecessarily remove current scheduling capability.
- Define one deterministic effective-reminder rule based on smallest ranking value, with explicit tie-breaking.
- Keep reminder prompt delivery gated by the same safe-execution conditions already used for wakeups.
- Expose inspection state that clearly separates "selected/effective versus blocked" from "scheduled versus overdue versus executing".

**Non-Goals:**

- Adding durable reminder persistence or recovery across gateway restart.
- Projecting reminder management through a new `houmao-mgr agents gateway reminders ...` CLI surface or new managed-agent `/houmao/agents/{agent_ref}/gateway/reminders` routes.
- Changing `mail-notifier` semantics or turning notifier control into generic reminder persistence.
- Preserving `/v1/wakeups` as a compatibility alias after the refactor lands.

## Decisions

### 1. Reminders keep the current scheduling model and add ranking-based arbitration

Each reminder will keep the current due-time model from wakeups:

- exactly one of `start_after_seconds` or `deliver_at_utc`
- `mode = "one_off"` or `mode = "repeat"`
- `interval_seconds` required only for repeating reminders

On top of that, every reminder record adds:

- `title`
- `prompt`
- `ranking`
- `paused`

This keeps the behavioral change focused on reminder-set arbitration rather than also inventing a new timer model. The user request requires richer selection and pause semantics, not removal of one-off or repeating delivery.

Alternative considered:

- Remove repeating reminders and collapse the scheduler to one-off due times only. Rejected because it would widen the breaking surface without solving a user-requested problem.

### 2. Reminder selection uses one total ordering and only one reminder is effective at a time

The runtime will compute reminder priority with a deterministic total order:

1. `ranking` ascending
2. `created_at` ascending
3. `reminder_id` ascending

The first reminder in that order is the effective reminder. All other reminders are blocked, even if they are already due. This makes ranking semantics deterministic and testable, including equal-ranking cases.

Alternative considered:

- Skip paused reminders when choosing the effective reminder. Rejected because the requested behavior explicitly says a paused reminder still takes the ranking and blocks others.

### 3. Paused is a delivery control flag, not a selection flag

`paused` stops prompt submission for that reminder, but it does not remove the reminder from ranking arbitration. A paused effective reminder therefore blocks lower-priority reminders from dispatch. Inspection responses will show both that the reminder is effective and that it is paused.

This keeps the user-visible rule simple: ranking decides who owns the live reminder slot; pause decides whether that selected reminder is allowed to emit prompts.

### 4. Reminder inspection separates selection state from delivery state

The current wakeup inspection model has one `state` field with values such as `scheduled`, `overdue`, and `executing`. That is not expressive enough once a reminder can be effective or blocked independently of whether it is due.

The reminder inspection model should therefore expose two axes:

- selection state: `effective` or `blocked`
- delivery state: `scheduled`, `overdue`, or `executing`

The collection response should also expose the current `effective_reminder_id` so callers can see the arbitration outcome without reimplementing ordering logic. Individual reminder inspection should expose enough data to explain blocking, such as `blocked_by_reminder_id`.

Alternative considered:

- Keep a single state enum that encodes every combined case. Rejected because it explodes the state space and makes clients reason about mixed concerns through one overloaded field.

### 5. The HTTP surface becomes resource-oriented around reminders

The reminder HTTP surface will be:

- `POST /v1/reminders`
- `GET /v1/reminders`
- `GET /v1/reminders/{reminder_id}`
- `PUT /v1/reminders/{reminder_id}`
- `DELETE /v1/reminders/{reminder_id}`

`POST /v1/reminders` accepts a list of reminder definitions and returns the created reminder records. `PUT /v1/reminders/{reminder_id}` updates mutable fields such as title, prompt, ranking, paused, and due-time configuration for one reminder. Separate `/pause` or `/resume` action routes are not needed because pause is just one mutable property on the reminder resource.

Alternative considered:

- Add action-style routes such as `/v1/reminders/{id}/pause` and `/resume`. Rejected because the gateway already uses ordinary `PUT` for mutable singleton control like `mail-notifier`, and the reminder fields form a normal resource state rather than one-off commands.

### 6. Reminder execution keeps the current gateway-owned low-priority execution gate

When the effective reminder is due, the gateway will continue to submit its prompt only when:

- request admission is open
- no terminal-mutating execution is active
- durable public queue depth is zero

If the effective reminder is due but the gateway is busy, it stays overdue in memory and is retried later. If the effective reminder is paused, the runtime does not submit the prompt and lower-ranked reminders remain blocked. Repeating reminders continue to maintain at most one pending due occurrence and do not burst to catch up after a busy window.

This preserves the current safety posture and keeps reminders out of the public request-kind surface.

### 7. The change is a clean API replacement with no `/v1/wakeups` alias

The design intentionally removes `/v1/wakeups` instead of keeping a deprecated alias. The repository currently prefers clarity over backward-compatibility shims, and carrying both route families would complicate models, docs, tests, and skill guidance for a feature that is explicitly being renamed and redefined.

## Risks / Trade-offs

- [A low-ranked paused reminder can starve every other reminder indefinitely] -> Make this blocking behavior explicit in the spec, inspection model, and skill/docs guidance so callers understand the consequence of pause plus ranking.
- [Breaking the route and payload model can surprise current direct HTTP callers] -> Keep the migration surface explicit in proposal, spec, and docs updates, and remove old naming atomically in tests and skill guidance.
- [The richer inspection model increases implementation and test complexity] -> Use one deterministic ordering rule and separate selection versus delivery state so tests can cover behavior without ambiguous combined enums.
- [Keeping repeat support while changing the resource model still leaves significant runtime complexity] -> Reuse the current due-time and no-burst cadence logic rather than redesigning scheduling and arbitration simultaneously.

## Migration Plan

1. Replace gateway models, client methods, and HTTP routes from wakeups to reminders in one change.
2. Update runtime scheduling from independent wakeup nomination to ranked effective-reminder arbitration.
3. Update gateway tests to cover batch creation, ranking order, paused blocking, due-time gating, and route renames.
4. Update packaged `houmao-agent-gateway` skill assets and CLI reference docs to remove wakeup terminology and describe reminders instead.
5. Remove direct `/v1/wakeups` guidance and tests in the same change so the repo does not carry dual terminology.

There is no persisted data migration because wakeups are already in-memory only. Rollback before release is straightforward: restore the old route family and models together.

## Open Questions

None for the proposal stage. The intended behavior is specific enough to fix the core contract now: signed ranking values, paused effective reminders block lower-ranked reminders, and reminder delivery stays live-gateway and non-durable.
