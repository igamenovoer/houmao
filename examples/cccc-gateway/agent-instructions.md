# CCCC Chat Instructions for an Agent

Use `houmao-cccc --instance "$PLUGIN_INSTANCE" binding` to inspect the selected binding. Inside a managed agent the CLI verifies and uses the owning gateway. An operator can also specify its base URL with `--gateway-url`. For Mail or an explicit delivery retry, obtain `BINDING_ID` from the binding result.

Run `members` for the current connection token and select one or more explicit Actor recipients. Use `@user` by itself to contact the Group's human.

```bash
houmao-cccc --instance "$PLUGIN_INSTANCE" members
houmao-cccc --instance "$PLUGIN_INSTANCE" chat send \
  --connection-token "$CONNECTION_TOKEN" --operation-id UNIQUE_OPERATION_ID \
  --to PEER_ACTOR_ID --mode request_reply --text 'Please check this result.'
```

An incoming CCCC request shows your Actor and Group, the gateway URL, and the relevant endpoints. One request fence contains the ordered messages. Each entry includes its sender, original timestamp, mode, text, and handle. Apply your current instructions and tool permissions to each request.

Use the handle from the exact message you want to reply to. Choose a fresh operation ID for each new reply.

```bash
houmao-cccc chat details --handle "$HANDLE"
houmao-cccc chat reply --handle "$HANDLE" \
  --operation-id "$NEW_OPERATION_ID" --text="$REPLY_TEXT"
```

For HTTP, use the base URL and the relative reply path in the header. Send JSON with `handle`, `operation_id`, and `text`. If the handle expires, select the exact event with `chat history --event-id EVENT_ID` to get a current handle.

A stored event may remain pending while the other agent is busy or its gateway is down. Check `chat deliveries --event-ref "$EVENT_REF"` using the scoped reference from a send or history result. An uncertain receipt means delivery may already have occurred. If a send response is lost, repeat the same request with its original operation ID to reconcile storage. Use `chat retry --binding-id "$BINDING_ID" --event-ref "$EVENT_REF" --to PEER_ACTOR_ID` for a fresh attempt after a terminal failure. An uncertain attempt requires `--allow-uncertain-retry`.

Use `chat history --limit 20` with the returned cursor to inspect further pages. History lookup leaves both prompt delivery and the Mail cursor untouched. Use `discovery` for the selected CCCC endpoint, Group, Actor registration, and operations available for an authorized direct call. Without a gateway, select the operator-provisioned private Actor profile with `--direct-profile` and use `chat pull` for a single ordered result.

## Deferred Mail

Check the effective Mail capability before using `mail` commands. Mail targets only Group Actors and forces native deferred mode:

```bash
houmao-cccc --gateway-url "$GATEWAY_BASE_URL" --instance "$PLUGIN_INSTANCE" mail send \
  --binding-id "$BINDING_ID" --operation-id UNIQUE_SEND_ID \
  --to PEER_ACTOR_ID --text 'Please review this in your next batch.'
houmao-cccc --gateway-url "$GATEWAY_BASE_URL" --instance "$PLUGIN_INSTANCE" mail cursor
houmao-cccc --gateway-url "$GATEWAY_BASE_URL" --instance "$PLUGIN_INSTANCE" mail peek \
  --limit 20 --max-bytes 262144
houmao-cccc --gateway-url "$GATEWAY_BASE_URL" --instance "$PLUGIN_INSTANCE" mail read \
  --binding-id "$BINDING_ID" --operation-id UNIQUE_READ_ID \
  --expected-cursor "$CURSOR_REF" --limit 20 --max-bytes 262144
```

Only `mail read` consumes the next ordered batch. Keep the returned receipt and operation ID. If its response is lost, use `mail reads --operation-id UNIQUE_READ_ID` and recover returned event references through exact `chat history` lookups. Do not generate a new read ID as a substitute for reconciliation. A matching repeated read returns the original decision, including a stable empty result, and does not consume the following batch.

Use `mail reply` with a returned `event_ref`, current binding, and a fresh operation ID to author deferred correspondence. Replying does not read or archive the parent. A content-free Mail notice alone does not consume the batch. Follow your task instructions before reading; unsupported email archive/move/unread/attachment actions do not apply to CCCC Mail. Email and CCCC errors never authorize implicit failover between systems.
