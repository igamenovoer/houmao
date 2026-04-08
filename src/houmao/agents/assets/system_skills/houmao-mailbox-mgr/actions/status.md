# Inspect Mailbox Root Status

Use this action only when the user wants mailbox-root health, registration counts, or project-aware root-selection detail.

## Workflow

1. Determine whether the task targets one arbitrary filesystem mailbox root or the active project mailbox root.
2. Use the `houmao-mgr` launcher already chosen by the top-level skill.
3. Run the matching mailbox-root status command.
4. Report the root status payload and keep the mailbox-root lane explicit.

## Command Shape

Use one of:

```text
<chosen houmao-mgr launcher> mailbox status [--mailbox-root <path>]
<chosen houmao-mgr launcher> project mailbox status
```

## Guardrails

- Do not reinterpret mailbox-root status as actor-scoped mailbox `status`.
- Do not ask for an address when the task is root-level status only.
