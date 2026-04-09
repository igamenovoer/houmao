# Send A New Message

Use this action for ordinary managed-agent outbound shared mailbox messages.

If the caller is acting as operator and needs to leave an operator-origin note in a managed agent mailbox, use `actions/post.md` instead of ordinary `send`.

Use `POST /v1/mail/send` to create one new outbound shared mailbox message.

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/send" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"to":["recipient@houmao.localhost"],"subject":"...","body_content":"...","attachments":[]}'
```

Use the exact `gateway.base_url` resolved for this turn.

When no live gateway facade is available, use the supported managed fallback surface instead:

```bash
houmao-mgr agents mail send --to recipient@houmao.localhost --subject "..." --body-content "..."
```
