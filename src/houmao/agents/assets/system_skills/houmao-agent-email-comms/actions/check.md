# Check Mail Through The Gateway

Use `POST /v1/mail/check` to inspect the current mailbox state through the live shared gateway facade.

Typical unread check:

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/check" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"unread_only":true,"limit":10}'
```

When no live gateway facade is available, use the supported managed fallback surface instead:

```bash
houmao-mgr agents mail check --unread-only --limit 10
```

Use the response to inspect current unread headers and any returned message detail for the turn.
