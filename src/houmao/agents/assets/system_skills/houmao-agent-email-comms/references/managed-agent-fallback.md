# Managed Mail Fallback Surface

Use this surface when `houmao-mgr agents mail resolve-live` returns `gateway: null` or when the task explicitly needs the managed-agent mailbox seam instead of direct shared gateway HTTP.

## Supported commands

```text
houmao-mgr agents mail status
houmao-mgr agents mail list
houmao-mgr agents mail peek --message-ref <opaque message_ref>
houmao-mgr agents mail read --message-ref <opaque message_ref>
houmao-mgr agents mail send ...
houmao-mgr agents mail post ...
houmao-mgr agents mail reply --message-ref <opaque message_ref> ...
houmao-mgr agents mail mark --message-ref <opaque message_ref> --answered
houmao-mgr agents mail move --message-ref <opaque message_ref> --destination-box archive
houmao-mgr agents mail archive --message-ref <opaque message_ref>
```

Use only the structured fields returned by `houmao-mgr agents mail resolve-live` for mailbox identity, transport, and fallback inputs.

`post` is filesystem-only in v1 and refuses live TUI submission fallback.

If a fallback `houmao-mgr agents mail ...` result returns `authoritative: false`, treat it as submission-only and verify outcome before assuming the mutation completed.
