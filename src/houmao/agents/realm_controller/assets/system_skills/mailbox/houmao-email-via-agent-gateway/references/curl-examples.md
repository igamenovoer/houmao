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

## Check unread

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/check" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"unread_only":true,"limit":10}'
```

## Send

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/send" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"to":["recipient@agents.localhost"],"subject":"...","body_content":"...","attachments":[]}'
```

## Reply

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/reply" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"message_ref":"<opaque message_ref>","body_content":"...","attachments":[]}'
```

## Mark read

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/state" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"message_ref":"<opaque message_ref>","read":true}'
```
