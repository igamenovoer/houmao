# Check Mailbox Status

Use mailbox status when you need to confirm mailbox identity, current transport, or live gateway availability before taking action.

When a live shared gateway mailbox facade is already available, use:

```bash
curl -sS "$GATEWAY_BASE_URL/v1/mail/status"
```

When no live gateway facade is available for this turn, run the direct fallback command:

```bash
<chosen houmao-mgr launcher> agents self mail status
```

Treat the returned mailbox identity and transport fields as the current supported state for this turn.
