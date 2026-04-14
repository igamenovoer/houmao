# Clear Delivered Mailbox Messages

Use this action only when the user wants to remove delivered filesystem mailbox messages while preserving mailbox accounts and registrations.

## Workflow

1. Determine whether the task targets one arbitrary filesystem mailbox root or the active project mailbox root.
2. Preserve explicit `--dry-run` or `--yes` intent when the user supplied it.
3. Use the `houmao-mgr` launcher already chosen by the top-level skill.
4. Run the matching mailbox message-clear command.
5. Report planned, applied, blocked, and preserved actions from the payload.

## Command Shape

Use one of:

```text
<chosen houmao-mgr launcher> mailbox clear-messages [--mailbox-root <path>] [--dry-run] [--yes]
<chosen houmao-mgr launcher> project mailbox clear-messages [--dry-run] [--yes]
```

## Guardrails

- Do not use this action to remove mailbox accounts; use mailbox unregister for account deregistration.
- Do not use mailbox cleanup for this task; cleanup removes inactive or stashed registrations and preserves canonical message history.
- Do not hand-edit mailbox-root files when this maintained command covers the request.
- Explain that external `path_ref` attachment targets are outside the clear operation.
