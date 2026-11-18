# Scoped Mail Commands

Resolve the current managed session once and select the offline or online binding for this work.

```bash
houmao-mgr agents self mail resolve-live
houmao-mgr agents self mail status
houmao-mgr agents self mail list --channel "$MAIL_CHANNEL" --expected-binding-id "$BINDING_ID" --box inbox
houmao-mgr agents self mail mark --channel "$MAIL_CHANNEL" --expected-binding-id "$BINDING_ID" --message-ref "$MESSAGE_REF" --read
```

With an attached gateway, the command verifies and signs the challenge using the current managed generation. End the operation on proof refusal, unavailable policy, or a binding conflict. Use the existing owner-authorized command path when the gateway is detached. A submission-only result requires separate verification.
