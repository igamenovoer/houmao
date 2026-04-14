# Shared Gateway Mailbox Endpoint Contract

Use these routes against the exact gateway base URL already present in the current prompt or recent mailbox context. When current context does not provide that URL, resolve it through:

```bash
houmao-mgr agents mail resolve-live
```

## Routes

- `GET /v1/mail/status`
- `POST /v1/mail/list`
- `POST /v1/mail/peek`
- `POST /v1/mail/read`
- `POST /v1/mail/send`
- `POST /v1/mail/post`
- `POST /v1/mail/reply`
- `POST /v1/mail/mark`
- `POST /v1/mail/move`
- `POST /v1/mail/archive`

## Payload shapes

- `GET /v1/mail/status`
  no request body
- `POST /v1/mail/list`
  `{"schema_version":1,"box":"inbox","read_state":"any","answered_state":"any","archived":false,"limit":10,"include_body":false}`
- `POST /v1/mail/peek`
  `{"schema_version":1,"message_ref":"<opaque message_ref>"}`
- `POST /v1/mail/read`
  `{"schema_version":1,"message_ref":"<opaque message_ref>"}`
- `POST /v1/mail/send`
  `{"schema_version":1,"to":["recipient@houmao.localhost"],"subject":"...","body_content":"...","attachments":[]}`
- `POST /v1/mail/post`
  `{"schema_version":1,"subject":"...","body_content":"...","attachments":[]}`
- `POST /v1/mail/reply`
  `{"schema_version":1,"message_ref":"<opaque message_ref>","body_content":"...","attachments":[]}`
- `POST /v1/mail/mark`
  `{"schema_version":1,"message_refs":["<opaque message_ref>"],"read":true,"answered":true}`
- `POST /v1/mail/move`
  `{"schema_version":1,"message_refs":["<opaque message_ref>"],"destination_box":"archive"}`
- `POST /v1/mail/archive`
  `{"schema_version":1,"message_refs":["<opaque message_ref>"]}`
