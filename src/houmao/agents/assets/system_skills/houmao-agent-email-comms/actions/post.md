# Post An Operator-Origin Note

Use this action when the caller is acting as operator and needs to deliver one operator-origin note into a managed agent mailbox.

When the caller is outside the Houmao managed-agent runtime, or current discovery shows there is no usable live gateway for the current session, use the authoritative operator surface:

```bash
houmao-mgr agents mail post --subject "..." --body-content "..." --reply-policy none
```

When the exact target managed-agent `gateway.base_url` is already known for this turn, `POST /v1/mail/post` is also supported:

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/post" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"subject":"...","body_content":"...","reply_policy":"operator_mailbox","attachments":[]}'
```

Use the exact `gateway.base_url` resolved for the selected managed agent when taking the gateway route.

This action is filesystem-only in v1. It delivers from the reserved sender `HOUMAO-operator@houmao.localhost`, refuses Stalwart-backed execution, and does not allow live TUI submission fallback.

Use `reply_policy=none` for the default no-reply operator note. Use `reply_policy=operator_mailbox` only when the recipient should reply back to the reserved operator mailbox.
