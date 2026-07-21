# List Mailbox Accounts

Use this action only when the user wants operator-facing mailbox registrations under one mailbox root.

## Workflow

1. Determine whether the task targets one arbitrary filesystem mailbox root or the active project mailbox root.
2. Use the `houmao-mgr` launcher already chosen by the top-level skill.
3. Run the matching mailbox accounts list command.
4. Report the listed registrations without inventing extra filtering.


If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.
## Command Shape

```bash
<chosen houmao-mgr launcher> mailbox accounts list [--mailbox-root <root>]
<chosen houmao-mgr launcher> project mailbox accounts list
```

## Guardrails

- Do not ask for an address when the task is only to list accounts.
- Do not reinterpret this action as actor-scoped inbox listing.
