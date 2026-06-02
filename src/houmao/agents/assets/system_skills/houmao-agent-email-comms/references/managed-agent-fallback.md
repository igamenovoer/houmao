# Managed Mail Fallback Surface

Use this surface when `houmao-mgr agents self mail resolve-live` returns `gateway: null` or when the task explicitly needs the managed-agent mailbox seam instead of direct shared gateway HTTP.

## Supported templates

```text
agents.self.mail.status
agents.self.mail.list
agents.self.mail.peek
agents.self.mail.read
agents.self.mail.send
agents.self.mail.post
agents.self.mail.reply
agents.self.mail.mark
agents.self.mail.move
agents.self.mail.archive
agents.single.mail.status
agents.single.mail.list
agents.single.mail.send
```

Use `internals command-templates show|render` for the selected template id, and use only the structured fields returned by `agents.self.mail.resolve-live` or `agents.single.mail.resolve-live` for mailbox identity, transport, and fallback inputs.

`post` is filesystem-only in v1 and refuses live TUI submission fallback.

If a fallback `houmao-mgr agents self mail ...` or `houmao-mgr agents single ... mail ...` result returns `authoritative: false`, treat it as submission-only and verify outcome before assuming the mutation completed.
