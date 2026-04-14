# Curl Examples

Set the base URL from the current prompt or recent mailbox context when it is already available. Otherwise resolve it from the manager-owned helper:

```bash
GATEWAY_BASE_URL="$(houmao-mgr agents mail resolve-live | jq -r '.gateway.base_url')"
```

Then use curl:

## Status

```bash
curl -sS "$GATEWAY_BASE_URL/v1/mail/status"
```

## List unread

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/list" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"box":"inbox","read_state":"unread","answered_state":"any","archived":false,"limit":10}'
```

## Peek

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/peek" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"message_ref":"<opaque message_ref>"}'
```

## Read

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/read" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"message_ref":"<opaque message_ref>"}'
```

## Send

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/send" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"to":["recipient@houmao.localhost"],"subject":"...","body_content":"...","attachments":[]}'
```

## Post operator-origin note

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/post" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"subject":"...","body_content":"...","attachments":[]}'
```

## Reply

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/reply" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"message_ref":"<opaque message_ref>","body_content":"...","attachments":[]}'
```

## Archive processed mail

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/archive" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"message_refs":["<opaque message_ref>"]}'
```
