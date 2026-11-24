# Managed Mail Fallback Surface

Use this surface when `houmao-mgr agents self mail resolve-live` returns `gateway: null` or when the task explicitly needs the managed-agent mailbox seam instead of direct shared gateway HTTP.

## Supported Commands

```bash
<chosen houmao-mgr launcher> agents self mail status
<chosen houmao-mgr launcher> agents self mail list --channel <channel> --expected-binding-id <binding_id>
<chosen houmao-mgr launcher> agents self mail peek --channel <channel> --expected-binding-id <binding_id> --message-ref <message_ref>
<chosen houmao-mgr launcher> agents self mail read --channel <channel> --expected-binding-id <binding_id> --message-ref <message_ref>
<chosen houmao-mgr launcher> agents self mail send --channel <channel> --expected-binding-id <binding_id> --to <recipient> --subject <subject> --body-content <body>
<chosen houmao-mgr launcher> agents self mail reply --channel <channel> --expected-binding-id <binding_id> --message-ref <message_ref> --body-content <body>
<chosen houmao-mgr launcher> agents self mail mark --channel <channel> --expected-binding-id <binding_id> --message-ref <message_ref> --read
<chosen houmao-mgr launcher> agents self mail move --channel <channel> --expected-binding-id <binding_id> --message-ref <message_ref> --destination-box <box>
<chosen houmao-mgr launcher> agents self mail archive --channel <channel> --expected-binding-id <binding_id> --message-ref <message_ref>
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> mail status
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> mail list --channel <channel> --expected-binding-id <binding_id>
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> mail send --channel <channel> --expected-binding-id <binding_id> --to <recipient> --subject <subject> --body-content <body>
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> mail post --channel offline --expected-binding-id <binding_id> --subject <subject> --body-content <body>
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> mail peek --channel offline --expected-binding-id <binding_id> --message-ref <post_ref>
```

Use only the structured fields returned by `agents self mail resolve-live` or `agents single ... mail resolve-live` for mailbox identity, transport, and fallback inputs.

`post` is filesystem-only in v1 and refuses live TUI submission fallback.

A fallback result with `authoritative: false` reports request status. Preserve its request ID and original scope. Use authorized read-only inspection to reconcile uncertain writes. Report an unresolved outcome if the read is unavailable or inconclusive.
