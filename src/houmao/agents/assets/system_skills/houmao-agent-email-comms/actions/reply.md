# Reply To One Message

Use `POST /v1/mail/reply` with the opaque `message_ref` of the message you are replying to.

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/reply" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"message_ref":"<opaque message_ref>","body_content":"...","attachments":[]}'
```

Do not reconstruct transport-local threading identifiers yourself.

When no live gateway facade is available, render `agents.mail.reply`, then run the rendered `argv`:

```text
agents.mail.reply
```
