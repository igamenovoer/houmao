# Decide What To Read

Use `POST /v1/mail/peek` to inspect one selected message without marking it read. Use `POST /v1/mail/read` only when you intentionally want to inspect the message and mark it read.

Use `POST /v1/mail/list` to inspect the current inbox queue, then choose which `message_ref` to act on next.

Treat `message_ref` and `thread_ref` as opaque identifiers.

Peek example:

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/peek" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"message_ref":"<opaque message_ref>"}'
```

Read example:

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/read" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"message_ref":"<opaque message_ref>"}'
```

When multiple open messages exist:

- use the metadata returned by `list`,
- choose the message or messages to inspect,
- re-list if the inbox snapshot may have changed before taking more actions.

When no live gateway facade is available, use `houmao-mgr agents mail peek` or `houmao-mgr agents mail read` for the selected message.
