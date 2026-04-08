# Clean Mailbox Root Registrations

Use this action only when the user wants to remove inactive or stashed mailbox registrations while preserving canonical message history.

## Workflow

1. Determine whether the task targets one arbitrary filesystem mailbox root or the active project mailbox root.
2. Preserve explicit age-threshold or `--dry-run` inputs when the user supplied them.
3. Use the `houmao-mgr` launcher already chosen by the top-level skill.
4. Run the matching mailbox cleanup command.
5. Report planned or applied cleanup actions from the payload.

## Command Shape

Use one of:

```text
<chosen houmao-mgr launcher> mailbox cleanup [--mailbox-root <path>] [--inactive-older-than-seconds <n>] [--stashed-older-than-seconds <n>] [--dry-run]
<chosen houmao-mgr launcher> project mailbox cleanup [--inactive-older-than-seconds <n>] [--stashed-older-than-seconds <n>] [--dry-run]
```

## Guardrails

- Do not imply that cleanup deletes canonical mailbox `messages/` history.
- Do not use this action when the user asked to remove one specific mailbox account; use mailbox unregister instead.
