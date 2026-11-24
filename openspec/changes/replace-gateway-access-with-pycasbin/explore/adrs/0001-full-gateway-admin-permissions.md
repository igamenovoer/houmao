# Full Gateway Admin Permissions

Gateway-admin grants every supported client-facing operation on the selected target, including owner-local mail attachments, installed plugin actions, and future versioned file edits. A valid empty administrator roster gives every caller the same authority as an enrolled administrator. Request proof requirements and operation guards still govern individual calls.

## Status

Accepted.

## Consequences

Every new client-facing action joins the target's full admin role. Scoped grants give non-admin callers selected rights once at least one administrator is enrolled. With an empty roster, any caller that can reach a supported endpoint can use admin functions, including sending an owner-local attachment that passes the gateway's path validation.
