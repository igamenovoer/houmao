# List Mailbox Accounts

Use this action only when the user wants operator-facing mailbox registrations under one mailbox root.

## Workflow

1. Determine whether the task targets one arbitrary filesystem mailbox root or the active project mailbox root.
2. Use the `houmao-mgr` launcher already chosen by the top-level skill.
3. Run the matching mailbox accounts list command.
4. Report the listed registrations without inventing extra filtering.

## Template Rendering

Use one of these template ids, then run the rendered `argv`:

```text
mailbox.accounts.list
project.mailbox.accounts.list
```

## Guardrails

- Do not ask for an address when the task is only to list accounts.
- Do not reinterpret this action as actor-scoped inbox listing.
