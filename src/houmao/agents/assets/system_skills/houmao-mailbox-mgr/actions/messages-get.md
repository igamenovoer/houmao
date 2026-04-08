# Inspect One Structural Mailbox Message

Use this action only when the user wants one structurally projected message for one registered mailbox address.

## Workflow

1. Determine whether the task targets one arbitrary filesystem mailbox root or the active project mailbox root.
2. Require the mailbox address and canonical mailbox message id.
3. Use the `houmao-mgr` launcher already chosen by the top-level skill.
4. Run the matching mailbox messages get command.
5. Report the structural message payload and keep actor-scoped follow-up outside this action.

## Command Shape

Use one of:

```text
<chosen houmao-mgr launcher> mailbox messages get --address <full-address> --message-id <canonical-message-id> [--mailbox-root <path>]
<chosen houmao-mgr launcher> project mailbox messages get --address <full-address> --message-id <canonical-message-id>
```

## Guardrails

- Do not treat structural message inspection as permission to mutate participant-local state.
- Do not infer the mailbox address or message id from unrelated context.
