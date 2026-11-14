# Scoped Curl Examples

Use the exact `GATEWAY_BASE_URL`, explicit `MAIL_CHANNEL` (`offline` or `online`), and `EXPECTED_BINDING_ID` from this turn. A notifier round requires all three in its prompt. For ordinary mail only, recover missing values through `houmao-mgr agents self mail resolve-live` and explicit channel selection. Do not infer a channel from canonical identity.

Summary status does not select a channel:

```bash
curl -sS "$GATEWAY_BASE_URL/v1/mail/status"
```

List one metadata page, then choose a scoped reference. The default is 50, the maximum is 200, and counts refer to the returned page:

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/$MAIL_CHANNEL/list" \
  -H 'content-type: application/json' \
  --data "$(jq -cn --arg binding "$EXPECTED_BINDING_ID" \
    '{schema_version:3,expected_binding_id:$binding,box:"inbox",read_state:"unread",answered_state:"any",archived:false,limit:50}')"
```

Only continue when `has_more` is true and the round's explicit page/message budget permits another request. Preserve these filters and binding and add the opaque `cursor` returned as `next_cursor`; stop on a stale-cursor error. Never fetch all pages automatically.

Peek leaves read state unchanged. Change the final route to `read` to mark a selected message read. Inspect `content_complete` and any content-limit fields before treating the text as a complete message:

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/$MAIL_CHANNEL/peek" \
  -H 'content-type: application/json' \
  --data "$(jq -cn --arg binding "$EXPECTED_BINDING_ID" --arg ref "$MESSAGE_REF" \
    '{schema_version:3,expected_binding_id:$binding,message_ref:$ref}')"
```

A fresh send carries the expected binding too. Set recipient, subject, and body from the authorized request:

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/$MAIL_CHANNEL/send" \
  -H 'content-type: application/json' \
  --data "$(jq -cn --arg binding "$EXPECTED_BINDING_ID" --arg to "$RECIPIENT" \
    --arg subject "$SUBJECT" --arg body "$BODY" \
    '{schema_version:3,expected_binding_id:$binding,to:[$to],subject:$subject,body_content:$body,attachments:[]}')"
```

Reply after work succeeds, preserving the original scoped reference:

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/$MAIL_CHANNEL/reply" \
  -H 'content-type: application/json' \
  --data "$(jq -cn --arg binding "$EXPECTED_BINDING_ID" --arg ref "$MESSAGE_REF" --arg body "$BODY" \
    '{schema_version:3,expected_binding_id:$binding,message_ref:$ref,body_content:$body,attachments:[]}')"
```

Archive only after successful work and any required reply:

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/$MAIL_CHANNEL/archive" \
  -H 'content-type: application/json' \
  --data "$(jq -cn --arg binding "$EXPECTED_BINDING_ID" --arg ref "$MESSAGE_REF" \
    '{schema_version:3,expected_binding_id:$binding,message_refs:[$ref]}')"
```

Read HTTP errors as failures. A binding conflict ends the operation or round; do not fetch a replacement binding and replay the payload. For operator-origin posting, use the `post` action and its explicit backend support rather than impersonating an ordinary sender.
