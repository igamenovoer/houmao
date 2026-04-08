# Post An Operator-Origin Note

Use `POST /v1/mail/post` to deliver one operator-origin note into the current managed agent mailbox.

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/post" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"subject":"...","body_content":"...","attachments":[]}'
```

Use the exact `gateway.base_url` resolved for this turn.

When no live gateway facade is available, use the supported authoritative fallback surface instead:

```bash
houmao-mgr agents mail post --subject "..." --body-content "..."
```

This action is filesystem-only in v1. It delivers from the reserved sender `HOUMAO-operator@houmao.localhost`, refuses Stalwart-backed execution, and does not allow live TUI submission fallback.
