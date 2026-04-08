# Inspect One Mailbox Account

Use this action only when the user wants one operator-facing mailbox registration under one mailbox root.

## Workflow

1. Determine whether the task targets one arbitrary filesystem mailbox root or the active project mailbox root.
2. Require the full mailbox address.
3. Use the `houmao-mgr` launcher already chosen by the top-level skill.
4. Run the matching mailbox accounts get command.
5. Report the returned mailbox registration payload.

## Command Shape

Use one of:

```text
<chosen houmao-mgr launcher> mailbox accounts get --address <full-address> [--mailbox-root <path>]
<chosen houmao-mgr launcher> project mailbox accounts get --address <full-address>
```

## Guardrails

- Do not ask for a message id when the task is mailbox-account inspection.
- Do not reinterpret missing-account errors as a request to create the account.
