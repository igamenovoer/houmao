# Managed Mail Fallback Surface

Use this surface when `houmao-mgr agents self mail resolve-live` returns `gateway: null` or when the task explicitly needs the managed-agent mailbox seam instead of direct shared gateway HTTP.

## Supported Commands

```bash
<chosen houmao-mgr launcher> agents self mail status
<chosen houmao-mgr launcher> agents self mail list --channel <channel> --expected-binding-id <binding_id>
<chosen houmao-mgr launcher> agents self mail peek --channel <channel> --expected-binding-id <binding_id> --message-ref <message_ref>
<chosen houmao-mgr launcher> agents self mail read --channel <channel> --expected-binding-id <binding_id> --message-ref <message_ref>
<chosen houmao-mgr launcher> agents self mail send --channel <channel> --expected-binding-id <binding_id> --to <recipient> --subject <subject> --body-content <body>
<chosen houmao-mgr launcher> agents self mail post --channel <channel> --expected-binding-id <binding_id> --subject <subject> --body-content <body>
<chosen houmao-mgr launcher> agents self mail reply --channel <channel> --expected-binding-id <binding_id> --message-ref <message_ref> --body-content <body>
<chosen houmao-mgr launcher> agents self mail mark --channel <channel> --expected-binding-id <binding_id> --message-ref <message_ref> --read
<chosen houmao-mgr launcher> agents self mail move --channel <channel> --expected-binding-id <binding_id> --message-ref <message_ref> --destination-box <box>
<chosen houmao-mgr launcher> agents self mail archive --channel <channel> --expected-binding-id <binding_id> --message-ref <message_ref>
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> mail status
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> mail list --channel <channel> --expected-binding-id <binding_id>
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> mail send --channel <channel> --expected-binding-id <binding_id> --to <recipient> --subject <subject> --body-content <body>
```

Use only the structured fields returned by `agents self mail resolve-live` or `agents single ... mail resolve-live` for mailbox identity, transport, and fallback inputs.

`post` is filesystem-only in v1 and refuses live TUI submission fallback.

If a fallback `houmao-mgr agents self mail ...` or `houmao-mgr agents single ... mail ...` result returns `authoritative: false`, treat it as submission-only and verify outcome before assuming the mutation completed.
