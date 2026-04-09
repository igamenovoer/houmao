# Manage Gateway Reminders

Use this action when the attached agent needs one or more ranked live reminders and a live gateway is already attached.

## Workflow

1. Confirm that the task really wants a gateway-owned reminder rather than a durable external scheduler.
2. Use the `houmao-mgr` launcher already chosen by the top-level skill when managed-agent discovery is still needed.
3. Recover the reminder definitions from the current prompt first and recent chat context second when they were stated explicitly:
   - `title`
   - exactly one of `prompt` or `send_keys`
   - `ranking`
   - `paused`
4. For `send_keys` reminders, recover:
   - `send_keys.sequence`
   - `send_keys.ensure_enter`
5. Treat `title` as inspection metadata only. A `send_keys` reminder does not submit `title` or any `prompt` text when it fires.
6. If the task asks for exact special keys such as `<[Escape]>` or slash-command submission, prefer `send_keys` rather than `prompt`.
7. For pure special-key reminders that must not submit, set `send_keys.ensure_enter = false`. The default is `true`, which ensures one trailing `<[Enter]>`.
8. Reject unsupported `send_keys` reminders honestly: REST-backed and server-managed headless gateway targets cannot preserve exact tmux send-keys semantics and return HTTP `422` on create or update.
9. Recover the exact timing mode for each reminder:
   - `start_after_seconds`
   - `deliver_at_utc`
10. Recover whether each reminder is `one_off` or `repeat`.
11. Prefer the managed-agent reminder seam first:
   - `<chosen houmao-mgr launcher> agents gateway reminders list|get|create|set|remove ...`
   - `/houmao/agents/{agent_ref}/gateway/reminders...` only when the current task is already operating through pair-managed HTTP
12. Keep ranking numeric:
   - use `--ranking <int>` for exact placement
   - use `--before-all` to insert above the current minimum ranking
   - use `--after-all` to append below the current maximum ranking
13. Use direct live `{gateway.base_url}/v1/reminders...` only when the task genuinely needs the lower-level live HTTP contract and the exact live base URL is already known.
14. Report the effective reminder, blocked reminders, ranking order, the delivery kind of each reminder, and any paused reminder that is currently blocking lower-ranked items.

## Preferred CLI Surface

Inspection:

- `<chosen houmao-mgr launcher> agents gateway reminders list --agent-name gpu`
- `<chosen houmao-mgr launcher> agents gateway reminders get --agent-name gpu --reminder-id greminder-123`

Create:

- `<chosen houmao-mgr launcher> agents gateway reminders create --agent-name gpu --title "Check inbox" --mode one_off --prompt "Review the inbox now." --after-all --start-after-seconds 300`
- `<chosen houmao-mgr launcher> agents gateway reminders create --agent-name gpu --title "Dismiss dialog" --mode one_off --sequence "<[Escape]>" --no-ensure-enter --before-all --start-after-seconds 5`

Update:

- `<chosen houmao-mgr launcher> agents gateway reminders set --agent-name gpu --reminder-id greminder-123 --before-all`
- `<chosen houmao-mgr launcher> agents gateway reminders set --agent-name gpu --reminder-id greminder-123 --paused --deliver-at-utc 2026-04-09T12:00:00+00:00`

Delete:

- `<chosen houmao-mgr launcher> agents gateway reminders remove --agent-name gpu --reminder-id greminder-123`

## Direct Gateway Routes

- `POST {gateway.base_url}/v1/reminders`
- `GET {gateway.base_url}/v1/reminders`
- `GET {gateway.base_url}/v1/reminders/{reminder_id}`
- `PUT {gateway.base_url}/v1/reminders/{reminder_id}`
- `DELETE {gateway.base_url}/v1/reminders/{reminder_id}`

Representative create payload:

```json
{
  "schema_version": 1,
  "reminders": [
    {
      "title": "Refactor Follow-up",
      "mode": "repeat",
      "prompt": "Resume the partially finished refactor.",
      "ranking": -10,
      "paused": false,
      "start_after_seconds": 300,
      "interval_seconds": 300
    }
  ]
}
```

Representative send-keys reminder payload:

```json
{
  "schema_version": 1,
  "reminders": [
    {
      "title": "Dismiss dialog",
      "mode": "one_off",
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

## Guardrails

- Do not claim that reminders survive gateway stop or restart; they are process-local in-memory state.
- Do not skip the supported `houmao-mgr agents gateway reminders ...` or `/houmao/agents/{agent_ref}/gateway/reminders...` surfaces when they already satisfy the task.
- Do not create a repeating reminder without `interval_seconds`.
- Do not set both `start_after_seconds` and `deliver_at_utc` in the same request.
- Do not set both `prompt` and `send_keys` in the same reminder, and do not omit both.
- Do not forget that `send_keys.ensure_enter` defaults to `true`; pure control-key reminders such as `<[Escape]>` usually need `ensure_enter = false`.
- Do not claim that `send_keys` reminders support `escape_special_keys`; reminder send-keys intentionally use exact special-key semantics only.
- Do not hide backend limitations: unsupported `send_keys` reminders fail with HTTP `422` at create or update time.
- Do not describe pausing a reminder as promoting lower-ranked reminders automatically; a paused effective reminder still blocks them.
- Do not describe reminders as extending the durable public `POST /v1/requests` kinds.
