# Runtime Mail Model

## Rules

- Treat mail-driven lite loops as notifier-prompt-driven.
- Agents process one received mail event, optionally run one bounded follow-up tick, update state or artifacts, and end the turn.
- Do not tell agents to sleep, poll, tail logs, or wait in-chat for future mail.
- Future work is represented by mailbox state, SQLite state, run artifacts, notifier prompts, or operator prompts.

## Template Dispatch

- Read Houmao mail envelope facts from maintained mailbox surfaces.
- Read lite message type from the body prologue `Loop-Template-Type`.
- Use the matching generated receiver skill when a known type is present.
- Use generated fallback or repair guidance only when the execplan defines it.
