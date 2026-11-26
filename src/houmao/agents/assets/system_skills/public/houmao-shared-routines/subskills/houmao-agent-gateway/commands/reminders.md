# Manage Gateway Reminders

## Workflow

1. **Confirm live-only fit and attached gateway**: `/v1/reminders` is in-memory gateway process state that does not survive gateway detach/stop/restart (use self-mail in `houmao-adv-usage-pattern` when restart backlog durability is required).
2. **Recover reminder parameters** from explicit prompt or recent context before mutating:
   - `title` (inspection metadata only; never sent as prompt text on `send_keys` reminders).
   - `mode`: `one_off` or `repeat` (`repeat` requires `interval_seconds`).
   - Action (mutually exclusive, required): `prompt` text **or** `send_keys` (`sequence` + `ensure_enter`, which defaults to `true`; set `ensure_enter: false` for pure control keys like `<[Escape]>` that must not append `<[Enter]>`). Note: REST/headless/service/web non-tmux backends reject `send_keys` reminders with HTTP `422`.
   - Timing (mutually exclusive): `start_after_seconds` or `deliver_at_utc`.
   - Placement & state: numeric `--ranking <int>` (smaller = higher priority; only the highest-priority due unblocked reminder dispatches, and a `paused: true` top-ranked reminder still blocks lower-ranked reminders), `--before-all`, or `--after-all`.
3. **Prefer the scoped `houmao-mgr` reminder CLI** (`agents single|self ... gateway reminders {list|get|create|set|remove}`), using `/houmao/agents/{agent_ref}/gateway/reminders*` for pair-managed HTTP or `{gateway.base_url}/v1/reminders*` only when direct HTTP is required (see [../references/http-surface.md](../references/http-surface.md)).
4. **Verify mutations** from `status`, `reminder_id`, `ranking`, `paused`, and `next_due_at_utc` receipts, using `reminders get` or `reminders list` for full state.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from [../references/http-surface.md](../references/http-surface.md) and the user request, then execute the plan.

## CLI and Direct HTTP Shapes

```bash
<chosen houmao-mgr launcher> agents single --agent-id <id> gateway reminders create --title <title> --mode one_off --prompt <prompt> --start-after-seconds <sec> --after-all
<chosen houmao-mgr launcher> agents self gateway reminders create --title <title> --mode one_off --prompt <prompt> --start-after-seconds <sec> --after-all
<chosen houmao-mgr launcher> agents single --agent-id <id> gateway reminders set --reminder-id <id> [--title <title>] [--prompt <prompt>] [--paused | --no-paused]
<chosen houmao-mgr launcher> agents single --agent-id <id> gateway reminders get --reminder-id <id>
<chosen houmao-mgr launcher> agents single --agent-id <id> gateway reminders list
<chosen houmao-mgr launcher> agents single --agent-id <id> gateway reminders remove --reminder-id <id>
```

Direct HTTP (`POST|GET /v1/reminders`, `GET|PUT|DELETE /v1/reminders/{reminder_id}`):

```json
{
  "schema_version": 1,
  "reminders": [
    {
      "title": "Dismiss dialog",
      "mode": "one_off",
      "send_keys": { "sequence": "<[Escape]>", "ensure_enter": false },
      "ranking": -100,
      "paused": false,
      "start_after_seconds": 5
    }
  ]
}
```

## Guardrails

- DO NOT claim `/v1/reminders` survives gateway stop/restart, or claim pausing a higher-ranked reminder unblocks lower-ranked reminders automatically.
- DO NOT combine `prompt` and `send_keys`, combine `start_after_seconds` and `deliver_at_utc`, omit `interval_seconds` on `repeat`, invent `escape_special_keys` on reminder `send_keys`, or hide HTTP `422` rejections on non-TUI backends.
