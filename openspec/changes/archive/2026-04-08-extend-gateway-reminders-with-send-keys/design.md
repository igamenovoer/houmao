## Context

The current reminder contract supports only one delivery form: semantic prompt submission. That fits ordinary reminder text, but it does not cover exact control-input workflows such as sending `<[Escape]>`, submitting slash commands, or emitting raw terminal keys that must preserve tmux-style `<[key-name]>` semantics.

The gateway already has a separate raw control-input lane at `POST /v1/control/send-keys`. That lane differs from prompt delivery in three important ways:

- it is exact control input rather than semantic prompt text,
- it is only supported for gateways that can preserve local tmux key semantics,
- it has distinct end-of-sequence behavior from prompt submission because Enter is not implicit.

This change therefore extends the reminder model from "a scheduled prompt" to "a scheduled delivery action" while preserving the existing ranking, pause, and readiness-gating behavior.

## Goals / Non-Goals

**Goals:**

- Preserve the current reminder ranking, pause, and timing model.
- Support two mutually exclusive reminder delivery forms: semantic `prompt` and raw `send_keys`.
- Define a reminder-native send-keys payload with `sequence` and `ensure_enter`.
- Make `ensure_enter=true` the default so slash-command and command-submission reminders do not need to repeat `<[Enter]>` manually every time.
- Define `ensure_enter` as "ensure one trailing Enter" rather than "always append another Enter".
- Reject unsupported send-keys reminders at create or update time rather than failing only when they become due.
- Keep send-keys reminders on the existing direct live `/v1/reminders` surface instead of inventing a new CLI family or managed-agent projection.

**Non-Goals:**

- Adding a new `houmao-mgr agents gateway reminders ...` CLI family.
- Adding reminder persistence across gateway restart.
- Adding reminder-local whole-string literal escaping analogous to `escape_special_keys`.
- Changing the existing raw `POST /v1/control/send-keys` route shape for non-reminder callers.
- Expanding send-keys support to backends that still cannot preserve exact tmux key semantics.

## Decisions

### 1. Reminder delivery becomes a tagged choice between `prompt` and `send_keys`

Reminder definitions and inspection models will support exactly one of:

- `prompt`
- `send_keys`

The `send_keys` object will contain:

- `sequence`
- `ensure_enter`

`title` remains required for reminder inspection regardless of delivery kind. For send-keys reminders, `title` is metadata only and is not emitted to the target.

This keeps the resource model coherent: one reminder still represents one scheduled thing, but the delivery action is no longer hard-coded to prompt text.

Alternative considered:

- Add a top-level `send_keys` string while keeping `prompt` required. Rejected because it makes send-keys reminders ambiguous and forces the system to ignore one of two competing payloads.

### 2. `ensure_enter` means "ensure one trailing Enter", not "blindly append Enter"

The reminder send-keys payload uses `ensure_enter: bool = true`.

When `ensure_enter=true`, the gateway will normalize the raw control-input sequence so that the delivered sequence ends with exactly one Enter. If the caller already supplied a trailing `<[Enter]>`, the gateway will not append a second one.

When `ensure_enter=false`, the gateway will deliver the sequence exactly as supplied.

This matches the user intent behind the field name: callers should not infer that the gateway will always add another Enter even when one is already present.

Alternative considered:

- Keep `auto_enter` and always append Enter when true. Rejected because the name is misleading and the behavior would create avoidable double-submit footguns.

### 3. Reminder send-keys intentionally omits `escape_special_keys`

Reminder send-keys is explicitly for exact special-key semantics, not for whole-string literal escaping. The payload therefore omits `escape_special_keys` entirely.

The sequence still uses the existing gateway send-keys grammar, including `<[key-name]>` tokens. The difference is only that reminders do not expose the literal-escape override because that would widen the surface without serving the target use case.

Alternative considered:

- Copy the `POST /v1/control/send-keys` body shape exactly into reminders. Rejected because reminder send-keys should be a narrower, opinionated automation surface rather than a second fully generic raw-input endpoint.

### 4. Send-keys reminder support is validated at create and update time

The reminder runtime should not accept a send-keys reminder that the current gateway target could never execute.

To support that cleanly, the gateway execution adapter boundary should expose explicit raw-control support inspection, for example:

- supported / unsupported
- optional unsupported reason for HTTP `422`

`POST /v1/reminders` and `PUT /v1/reminders/{reminder_id}` will use that capability check when any submitted reminder uses `send_keys`.

This avoids a poor operator experience where a reminder appears valid for minutes or hours and only fails when it finally becomes due.

Alternative considered:

- Accept all send-keys reminders and fail only when due. Rejected because the current backend support matrix is static enough to reject earlier and more honestly.

### 5. Send-keys reminders reuse the same readiness gate as prompt reminders

Due effective send-keys reminders remain low-priority gateway-owned internal execution, not a separate urgent bypass lane.

They will still require:

- request admission open
- no active terminal-mutating execution
- zero durable public queue depth

This keeps reminder arbitration simple: delivery kind changes the action that is executed, not the ranking or scheduling semantics.

### 6. Inspection should surface delivery kind explicitly

Reminder inspection should include an explicit `delivery_kind`, with values:

- `prompt`
- `send_keys`

It should also include the active delivery payload fields needed for inspection. That avoids clients inferring behavior indirectly from nullable fields alone and makes mixed reminder sets easier to reason about.

Alternative considered:

- Infer delivery kind from `prompt is null`. Rejected because explicit delivery-kind state is easier to document, test, and inspect.

## Risks / Trade-offs

- [Default `ensure_enter=true` can surprise callers who only wanted a special key such as Escape] -> Keep the docs and skill guidance explicit that pure control-key reminders must set `ensure_enter=false`.
- [Reminder create/update now depends on adapter capability inspection] -> Add a simple adapter-level capability method rather than re-deriving support from backend names in multiple places.
- [A narrower reminder send-keys shape differs from `POST /v1/control/send-keys`] -> Document the difference clearly: reminders reuse the grammar but intentionally do not expose the literal-escape override.
- [Mixed prompt and send-keys reminders make inspection models richer] -> Add explicit `delivery_kind` and keep "exactly one delivery form" validation strict.

## Migration Plan

1. Extend reminder models with the new tagged delivery shape and `ensure_enter` default.
2. Update gateway runtime validation and execution to support prompt reminders and send-keys reminders under the same ranking and scheduling system.
3. Add adapter capability inspection so unsupported send-keys reminders fail at create or update time.
4. Update reminder tests for prompt/send-keys exclusivity, `ensure_enter` normalization, and unsupported backend rejection.
5. Update gateway skill assets and gateway reference docs to explain send-keys reminders and the `ensure_enter=false` opt-out case.

There is no persisted data migration because reminders remain in-memory only. Existing prompt reminders remain valid after the change.

## Open Questions

None for proposal scope. The intended behavior is specific enough to define now: exact one-of delivery selection, `ensure_enter` defaulting to `true`, and early rejection on unsupported send-keys backends.
