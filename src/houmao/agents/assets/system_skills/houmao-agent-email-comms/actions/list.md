# List Mail Through The Gateway

Use `POST /v1/mail/list` to inspect the current mailbox state through the live shared gateway facade.

Typical unread list:

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/list" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"box":"inbox","read_state":"unread","answered_state":"any","archived":false,"limit":10}'
```

When no live gateway facade is available, render `agents.mail.list`, then run the rendered `argv`:

```text
agents.mail.list
```

Use the response to inspect current unread headers and any returned message detail for the turn.
