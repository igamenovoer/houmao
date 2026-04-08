# Gateway Reminders

- Who this is for: operators and maintainers who need to understand the live gateway reminder surface without reading the raw HTTP contract first.
- What it explains: what reminders are, how ranking and pause semantics work, when reminders actually dispatch, and which boundaries are intentionally unsupported.
- Assumes: you already understand basic gateway attach and lifecycle concepts from [Lifecycle And Operator Flows](lifecycle.md).

## Mental Model

Gateway reminders are a direct live HTTP scheduling surface owned by one attached gateway process.

- They are not durable queue records.
- They are not mailbox backlog.
- They are not projected through the managed-agent `/houmao/agents/*` API.
- They exist only inside the current live gateway process and disappear on gateway restart.

The gateway keeps a live reminder set, chooses one effective reminder by ranking, and only that effective reminder is eligible to dispatch a reminder delivery.

## Supported Routes

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/v1/reminders` | create one or more reminders in one batch |
| `GET` | `/v1/reminders` | inspect the live reminder set and current effective reminder |
| `GET` | `/v1/reminders/{reminder_id}` | inspect one reminder |
| `PUT` | `/v1/reminders/{reminder_id}` | replace one reminder's mutable fields |
| `DELETE` | `/v1/reminders/{reminder_id}` | delete one reminder or stop future repeats after an already-started execution |

Use [Protocol And State Contracts](../contracts/protocol-and-state.md) for the exact JSON schema.

## Request Fields

Every reminder definition currently uses these fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `mode` | yes | `one_off` or `repeat` |
| `title` | yes | short human-readable label for inspection |
| `prompt` | conditional | exact prompt text the gateway will submit when a prompt reminder fires |
| `send_keys` | conditional | raw control-input payload for exact `<[key-name]>` delivery |
| `ranking` | yes | signed integer priority; smaller values win and may be negative |
| `paused` | no | defaults to `false`; paused reminders do not dispatch deliveries |
| `start_after_seconds` | conditional | relative start delay from the create or update time |
| `deliver_at_utc` | conditional | absolute UTC due time |
| `interval_seconds` | conditional | repeat cadence, required only for `mode = "repeat"` |

Timing rule:

- set exactly one of `start_after_seconds` or `deliver_at_utc`

Delivery rule:

- set exactly one of `prompt` or `send_keys`

`send_keys` fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `sequence` | yes | raw control-input sequence using the same exact `<[key-name]>` grammar as `POST /v1/control/send-keys` |
| `ensure_enter` | no | defaults to `true`; ensures one trailing `<[Enter]>` unless set to `false` |

Mode rule:

- `one_off` must not include `interval_seconds`
- `repeat` must include `interval_seconds`

## Delivery Kinds

Reminder inspection exposes `delivery_kind`:

- `prompt`: the reminder submits semantic prompt text from `prompt`
- `send_keys`: the reminder submits raw control input from `send_keys.sequence`

For `send_keys` reminders:

- `title` remains required for inspection and reporting
- the gateway does not submit `title`
- the gateway does not synthesize `prompt` text
- `escape_special_keys` is intentionally not available on reminders
- `ensure_enter=true` is the default and ensures one trailing `<[Enter]>`
- pure control-key reminders such as `<[Escape]>` usually need `ensure_enter=false`

## Effective Reminder Selection

The gateway always computes one effective reminder from the live set.

Selection order:

1. smallest `ranking`
2. earlier creation time
3. smaller opaque `reminder_id` as the final deterministic tie-break

This means higher-numbered reminders never "run in parallel" behind the winner. They remain blocked until the effective reminder is updated, deleted, or naturally leaves the live set.

## Selection State Versus Delivery State

Reminder responses expose two different axes:

| Field | Values | Meaning |
| --- | --- | --- |
| `selection_state` | `effective`, `blocked` | whether the reminder is currently selected to lead the set |
| `delivery_state` | `scheduled`, `overdue`, `executing` | whether the reminder is waiting for time, due but not yet delivered, or currently dispatching |

Common combinations:

- effective + scheduled: the winning reminder is not due yet
- effective + overdue: the winning reminder is due but still waiting for the gateway to become ready
- effective + executing: the winning reminder is currently submitting its configured delivery
- blocked + overdue: a lower-priority reminder is already due, but still cannot run because another reminder outranks it

## Pause Semantics

`paused` does not remove a reminder from ranking.

- a paused effective reminder still blocks all lower-priority reminders
- a paused reminder never submits its delivery while paused
- if a paused reminder later becomes blocked because another reminder was reranked ahead of it, it remains paused and blocked until updated again

This behavior is intentional. Pause means "keep this reminder in control, but suppress delivery."

## When A Reminder Actually Dispatches

Even a due effective reminder only dispatches when the gateway is ready:

- `request_admission = open`
- `active_execution = idle`
- durable queue depth is zero

If those conditions are not satisfied, the effective reminder stays live and reports `delivery_state = "overdue"` until the gateway becomes idle again.

Only the effective reminder is checked for dispatch. Lower-ranked reminders do not bypass a blocked effective reminder, even if they are also due.

When the gateway is ready:

- `prompt` reminders submit semantic prompt text
- `send_keys` reminders submit raw control input

Backend limit:

- send-keys reminders are accepted only when the attached target can preserve local tmux key semantics
- REST-backed and server-managed headless gateway targets reject send-keys reminders with HTTP `422` at create or update time

## One-Off And Repeat Behavior

One-off reminder:

- dispatches at its due time once
- leaves the live set after that execution finishes

Repeat reminder:

- dispatches first at `start_after_seconds` or `deliver_at_utc`
- then repeats by `interval_seconds`
- keeps anchored cadence and does not burst through every missed interval after a busy period

Representative one-off request:

```json
{
  "schema_version": 1,
  "reminders": [
    {
      "mode": "one_off",
      "title": "Check inbox",
      "prompt": "Review the inbox now.",
      "ranking": 0,
      "paused": false,
      "start_after_seconds": 300
    }
  ]
}
```

Representative repeat request:

```json
{
  "schema_version": 1,
  "reminders": [
    {
      "mode": "repeat",
      "title": "Inbox poll",
      "prompt": "Review the inbox again.",
      "ranking": -10,
      "paused": false,
      "start_after_seconds": 300,
      "interval_seconds": 300
    }
  ]
}
```

Representative send-keys request:

```json
{
  "schema_version": 1,
  "reminders": [
    {
      "mode": "one_off",
      "title": "Dismiss dialog",
      "send_keys": {
        "sequence": "<[Escape]>",
        "ensure_enter": false
      },
      "ranking": -100,
      "paused": false,
      "start_after_seconds": 5
    }
  ]
}
```

## Update And Delete Behavior

`PUT /v1/reminders/{reminder_id}` replaces the mutable reminder fields and immediately recomputes the effective reminder.

- changing `ranking` can promote or demote a reminder right away
- changing the timing fields resets the next due time from the update moment for `start_after_seconds`
- executing reminders currently reject updates with HTTP `409`

`DELETE /v1/reminders/{reminder_id}` behaves differently depending on state:

- scheduled or overdue reminder: removed immediately
- executing reminder: the already-started delivery continues, but future repeat executions are stopped

## Boundaries And Non-Goals

Current reminder boundaries are intentionally narrow:

- no `houmao-mgr agents gateway reminders ...` CLI family
- no managed-agent `/houmao/agents/{agent_ref}/gateway/reminders` projection
- no persistence across gateway restart
- no replay into the durable gateway request queue as a public request kind
- no reminder-local `escape_special_keys` override

Use reminders for live attached-gateway timing only. Use mailbox backlog when you need durable follow-up work across longer-lived failures or restarts.

## Common Confusions

- `start_after_seconds` is relative to the create or update time, not to gateway attach time.
- `paused` is not the same thing as blocked. A paused reminder can still be the effective reminder.
- `ranking` is not bounded and may be negative.
- `title` is inspection metadata; prompt reminders dispatch `prompt`, while send-keys reminders dispatch `send_keys.sequence`.
- `ensure_enter=true` does not mean "append another Enter no matter what"; it ensures one trailing `<[Enter]>`.
- `GET /v1/reminders` shows only the current live process state, not any durable history.

## See Also

- [Agent Gateway Reference](../index.md) — subsystem overview
- [Protocol And State Contracts](../contracts/protocol-and-state.md) — exact route and payload definitions
- [Gateway Mail-Notifier](mail-notifier.md) — gateway-owned polling loop for unread mailbox reminders

## Source References

- [`src/houmao/agents/realm_controller/gateway_models.py`](../../../../src/houmao/agents/realm_controller/gateway_models.py)
- [`src/houmao/agents/realm_controller/gateway_service.py`](../../../../src/houmao/agents/realm_controller/gateway_service.py)
- [`src/houmao/agents/realm_controller/gateway_client.py`](../../../../src/houmao/agents/realm_controller/gateway_client.py)
- [`tests/unit/agents/realm_controller/test_gateway_support.py`](../../../../tests/unit/agents/realm_controller/test_gateway_support.py)
- [`tests/integration/agents/realm_controller/test_gateway_runtime_contract.py`](../../../../tests/integration/agents/realm_controller/test_gateway_runtime_contract.py)
