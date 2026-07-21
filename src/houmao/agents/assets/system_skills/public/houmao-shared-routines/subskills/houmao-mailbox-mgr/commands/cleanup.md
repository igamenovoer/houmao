# Clean Mailbox Root Registrations

Use this action only when the user wants to remove inactive or stashed mailbox registrations while preserving canonical message history.

## Workflow

1. Determine whether the task targets one arbitrary filesystem mailbox root or the active project mailbox root.
2. Preserve explicit age-threshold or `--dry-run` inputs when the user supplied them.
3. Use the `houmao-mgr` launcher already chosen by the top-level skill.
4. Run the matching mailbox cleanup command.
5. Report planned or applied cleanup actions from the payload.


If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.
## Command Shape

```bash
<chosen houmao-mgr launcher> mailbox cleanup [--mailbox-root <root>] [--inactive-older-than-seconds <seconds>] [--stashed-older-than-seconds <seconds>] [--dry-run]
<chosen houmao-mgr launcher> project mailbox cleanup [--inactive-older-than-seconds <seconds>] [--stashed-older-than-seconds <seconds>] [--dry-run]
```

## Guardrails

- Do not imply that cleanup deletes canonical mailbox `messages/` history.
- Do not use this action when the user asked to remove one specific mailbox account; use mailbox unregister instead.
