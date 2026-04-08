# List Structural Mailbox Messages

Use this action only when the user wants structural message projections for one registered mailbox address.

## Workflow

1. Determine whether the task targets one arbitrary filesystem mailbox root or the active project mailbox root.
2. Require the mailbox address whose structural message projections should be listed.
3. Use the `houmao-mgr` launcher already chosen by the top-level skill.
4. Run the matching mailbox messages list command.
5. Report the structural message payload and keep the structural-only boundary explicit.

## Command Shape

Use one of:

```text
<chosen houmao-mgr launcher> mailbox messages list --address <full-address> [--mailbox-root <path>]
<chosen houmao-mgr launcher> project mailbox messages list --address <full-address>
```

## Guardrails

- Do not treat this action as unread-state inspection.
- Do not mark messages read, archived, or deleted from this action.
- Do not switch to `houmao-mgr agents mail ...` unless the user actually needs actor-scoped mailbox participation state.
