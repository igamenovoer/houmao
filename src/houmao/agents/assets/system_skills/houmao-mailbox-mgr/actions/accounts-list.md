# List Mailbox Accounts

Use this action only when the user wants operator-facing mailbox registrations under one mailbox root.

## Workflow

1. Determine whether the task targets one arbitrary filesystem mailbox root or the active project mailbox root.
2. Use the `houmao-mgr` launcher already chosen by the top-level skill.
3. Run the matching mailbox accounts list command.
4. Report the listed registrations without inventing extra filtering.

## Command Shape

Use one of:

```text
<chosen houmao-mgr launcher> mailbox accounts list [--mailbox-root <path>]
<chosen houmao-mgr launcher> project mailbox accounts list
```

## Guardrails

- Do not ask for an address when the task is only to list accounts.
- Do not reinterpret this action as actor-scoped inbox listing.
