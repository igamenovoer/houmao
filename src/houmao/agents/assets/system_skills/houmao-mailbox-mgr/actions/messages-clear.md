# Clear Messages For One Mailbox Account

Use this action only when the user wants to remove delivered filesystem mailbox messages visible to one selected mailbox address while preserving mailbox accounts, registrations, and other accounts' message visibility.

## Workflow

1. Determine whether the task targets one arbitrary filesystem mailbox root or the active project mailbox root.
2. Identify the selected mailbox address from explicit user input or recent context.
3. Preserve explicit `--dry-run` or `--yes` intent when the user supplied it.
4. Use the `houmao-mgr` launcher already chosen by the top-level skill.
5. Run the matching account-scoped mailbox message-clear command.
6. Report planned, applied, blocked, and preserved actions from the payload.

## Command Shape

```bash
<chosen houmao-mgr launcher> mailbox messages clear --address <address> [--mailbox-root <root>] [--dry-run] [--yes]
<chosen houmao-mgr launcher> project mailbox messages clear --address <address> [--dry-run] [--yes]
```

## Guardrails

- Do not use this action when the user wants to remove all delivered messages from the mailbox root; use `actions/clear-messages.md` for that all-account reset.
- Do not use this action to remove mailbox accounts; use mailbox unregister for account deregistration.
- Do not use mailbox cleanup for this task; cleanup removes inactive or stashed registrations and preserves canonical message history.
- Do not hand-edit mailbox-root files when this maintained command covers the request.
- Explain that external `path_ref` attachment targets are outside the clear operation.
