# Unregister A Mailbox Account

Use this action only when the user wants to deactivate or purge one filesystem mailbox registration under one mailbox root.

## Workflow

1. Determine whether the task targets one arbitrary filesystem mailbox root or the active project mailbox root.
2. Require the full mailbox address.
3. Preserve an explicit `deactivate` or `purge` mode when the user supplied one; otherwise let the command default to `deactivate`.
4. Use the `houmao-mgr` launcher already chosen by the top-level skill.
5. Run the matching mailbox deregistration command.
6. Report the resulting deregistration posture clearly.

## Command Shape

Use one of:

```text
<chosen houmao-mgr launcher> mailbox unregister --address <full-address> [--mailbox-root <path>] [--mode deactivate|purge]
<chosen houmao-mgr launcher> project mailbox unregister --address <full-address> [--mode deactivate|purge]
```

## Guardrails

- Do not reinterpret deregistration as mailbox-root cleanup.
- Do not guess whether the user wants `deactivate` or `purge` when they expressed a retention preference.
