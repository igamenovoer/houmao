# Repair A Mailbox Root

Use this action only when the user wants to rebuild filesystem mailbox index state under one mailbox root.

## Workflow

1. Determine whether the task targets one arbitrary filesystem mailbox root or the active project mailbox root.
2. Preserve explicit staging-cleanup or staging-quarantine flags when the user supplied them.
3. Use the `houmao-mgr` launcher already chosen by the top-level skill.
4. Run the matching mailbox repair command.
5. Report the repair result and any staging cleanup posture that mattered.

## Command Shape

Use one of:

```text
<chosen houmao-mgr launcher> mailbox repair [--mailbox-root <path>] [--cleanup-staging|--no-cleanup-staging] [--quarantine-staging|--remove-staging]
<chosen houmao-mgr launcher> project mailbox repair [--cleanup-staging|--no-cleanup-staging] [--quarantine-staging|--remove-staging]
```

## Guardrails

- Do not replace the repair action with manual mailbox-root file deletion.
- Do not use this action for late managed-agent binding problems unless the user also needs root repair.
