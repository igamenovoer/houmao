# Reply Hardening Contract and Reminder Template

Use reply hardening when the notifier or operator prompt asks for extra reply assurance (for example "must remember to reply", "harden reply action", or "use reminder to make sure you remember to reply").

## Rules

1. Create one `one_off` prompt reminder per reply-required `message_ref` **before** long processing begins and record its `reminder_id`.
2. Default `start_after_seconds` to `15` unless the prompt specifies another delay; never use `repeat` mode or `interval_seconds`.
3. Append at lowest priority: pass `--after-all` on `houmao-mgr agents self gateway reminders add`, or on direct `POST /v1/reminders` inspect current reminders first and set `ranking` to `max_ranking + 1`.
4. Embed exact `gateway_base_url`, `channel`, `expected_binding_id`, `message_ref`, `thread_ref` (or `unknown`), sender, subject, and recipient, instructing the wakeup turn to re-check reply state before calling `POST /v1/mail/{channel}/reply` so duplicate replies are never sent.
5. Remove any unfired reminder (`houmao-mgr agents self gateway reminders remove --reminder-id <reminder_id>` or `DELETE /v1/reminders/{reminder_id}`) as soon as the normal end-of-round reply succeeds.
6. Keep hardening scoped to reply assurance. Successful work and reply are prerequisites for ordinary archive, which also requires current placement capability. On a protected binding, report completion for owner filing.

## Prompt Template

```text
Reply hardening reminder.

Gateway: <exact gateway_base_url>; channel: <offline|online>; expected binding: <binding_id>
Stop on a missing context value or binding mismatch; never switch accounts or channels.

Mail: <message_ref>; thread: <thread_ref or unknown>; from: <sender>; subject: <subject>
Reply to: <reply recipient>

If this mail is still being processed and the work is not done, set this same one-off reminder again through the gateway with 15s and continue processing the email.

If this mail is already processed, reply to mail <message_ref>.
```

## Direct Gateway JSON Shape

Replace `1001` with `max_existing_ranking + 1`:

```json
{
  "schema_version": 1,
  "reminders": [
    {
      "title": "Reply required: <subject>",
      "mode": "one_off",
      "prompt": "<filled reminder prompt from the template above>",
      "ranking": 1001,
      "paused": false,
      "start_after_seconds": 15
    }
  ]
}
```
