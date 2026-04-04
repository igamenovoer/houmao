# Determine The Gateway Base URL

If the current prompt or recent mailbox context already provides the exact gateway base URL for this turn, use that value directly and do not rerun discovery.

Otherwise run:

```bash
houmao-mgr agents mail resolve-live
```

Use the structured JSON output from that command as the discovery contract for this turn.

When the output includes a `gateway` object:
- use `gateway.base_url` as the exact endpoint prefix for shared `/v1/mail/*` operations,
- keep using the opaque `message_ref` and `thread_ref` values returned by mailbox surfaces,
- do not guess a localhost port from unrelated process state.

When `gateway` is `null`, stop using this skill and fall back to the transport-specific Houmao mailbox skill for that session.
