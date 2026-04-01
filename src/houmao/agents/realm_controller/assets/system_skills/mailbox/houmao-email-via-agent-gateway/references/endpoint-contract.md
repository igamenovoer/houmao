# Shared Gateway Mailbox Endpoint Contract

Use these routes against the exact gateway base URL already present in the current prompt or recent mailbox context. When current context does not provide that URL, resolve it through:

```bash
houmao-mgr agents mail resolve-live
```

## Routes

- `GET /v1/mail/status`
- `POST /v1/mail/check`
- `POST /v1/mail/send`
- `POST /v1/mail/reply`
- `POST /v1/mail/state`

## Payload shapes

- `GET /v1/mail/status`
  no request body
- `POST /v1/mail/check`
  `{"schema_version":1,"unread_only":true,"limit":10}`
- `POST /v1/mail/send`
  `{"schema_version":1,"to":["recipient@agents.localhost"],"subject":"...","body_content":"...","attachments":[]}`
- `POST /v1/mail/reply`
  `{"schema_version":1,"message_ref":"<opaque message_ref>","body_content":"...","attachments":[]}`
- `POST /v1/mail/state`
  `{"schema_version":1,"message_ref":"<opaque message_ref>","read":true}`
