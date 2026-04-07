# Mark One Message Read

Mark a message read only after the corresponding mailbox action succeeds.

Use `POST /v1/mail/state` when a live gateway facade is available:

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/state" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"message_ref":"<opaque message_ref>","read":true}'
```

When no live gateway facade is available, use:

```bash
houmao-mgr agents mail mark-read --message-ref <opaque message_ref>
```

Do not treat detection of unread mail as an implicit read-state update.
