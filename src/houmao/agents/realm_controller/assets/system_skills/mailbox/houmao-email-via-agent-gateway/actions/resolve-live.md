# Resolve Live Mailbox Bindings

Run:

```bash
pixi run houmao-mgr agents mail resolve-live
```

Use the structured JSON output from that command as the discovery contract for this turn.

When the output includes a `gateway` object:
- use `gateway.base_url` as the exact endpoint prefix for shared `/v1/mail/*` operations,
- keep using the opaque `message_ref` and `thread_ref` values returned by mailbox surfaces,
- do not guess a localhost port from unrelated process state.

When `gateway` is `null`, stop using this skill and fall back to the transport-specific Houmao mailbox skill for that session.
