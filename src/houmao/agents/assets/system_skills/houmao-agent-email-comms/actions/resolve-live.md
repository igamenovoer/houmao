# Determine Current Mailbox Bindings

If the current prompt or recent mailbox context already provides the exact gateway base URL or current mailbox binding set for this turn, use that value directly and do not rerun discovery first.

Otherwise run:

```bash
houmao-mgr agents mail resolve-live
```

Use the structured JSON output from that command as the supported mailbox-discovery contract for this turn.

When the output includes a `gateway` object:

- use `gateway.base_url` as the exact endpoint prefix for shared `/v1/mail/*` operations,
- keep using the opaque `message_ref` and `thread_ref` values returned by mailbox surfaces,
- do not guess a localhost port from unrelated process state.

When `gateway` is `null`:

- use the `mailbox.transport` value to choose the matching transport page inside this skill,
- use the supported `houmao-mgr agents mail ...` fallback surface for that turn instead of guessing a direct shared-gateway endpoint.
