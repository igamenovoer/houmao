# Mark One Message Read

Mark a message read only after the corresponding mailbox action succeeds.

Use `POST /v1/mail/state`:

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/state" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"message_ref":"<opaque message_ref>","read":true}'
```

Do not treat detection of unread mail as an implicit read-state update.
