# Archive Processed Mail

Archive a message only after the corresponding mailbox action succeeds and any required reply has been sent successfully.

Use `POST /v1/mail/archive` when a live gateway facade is available:

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/archive" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"message_refs":["<opaque message_ref>"]}'
```

When no live gateway facade is available, use:

```bash
houmao-mgr agents mail archive --message-ref <opaque message_ref>
```

Do not treat detection, peeking, reading, or replying as an implicit archive operation. Reply marks the parent message answered; archive closes the processed inbox work.
