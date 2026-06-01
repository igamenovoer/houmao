# Managed Mail Fallback Surface

Use this surface when `houmao-mgr agents mail resolve-live` returns `gateway: null` or when the task explicitly needs the managed-agent mailbox seam instead of direct shared gateway HTTP.

## Supported templates

```text
agents.mail.status
agents.mail.list
agents.mail.peek
agents.mail.read
agents.mail.send
agents.mail.post
agents.mail.reply
agents.mail.mark
agents.mail.move
agents.mail.archive
```

Use `internals command-templates show|render` for the selected template id, and use only the structured fields returned by `agents.mail.resolve-live` for mailbox identity, transport, and fallback inputs.

`post` is filesystem-only in v1 and refuses live TUI submission fallback.

If a fallback `houmao-mgr agents mail ...` result returns `authoritative: false`, treat it as submission-only and verify outcome before assuming the mutation completed.
