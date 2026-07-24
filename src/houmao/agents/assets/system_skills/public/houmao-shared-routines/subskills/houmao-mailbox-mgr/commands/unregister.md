# Unregister A Mailbox Account

Use this action only when the user wants to deactivate or purge one filesystem mailbox registration under one mailbox root.

## Workflow

1. Determine whether the task targets one arbitrary filesystem mailbox root or the active project mailbox root.
2. Require the full mailbox address.
3. Preserve an explicit `deactivate` or `purge` mode when the user supplied one; otherwise let the command default to `deactivate`.
4. Use the `houmao-mgr` launcher already chosen by the top-level skill.
5. Run the matching mailbox deregistration command.
6. Report the resulting deregistration posture clearly.


If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.
## Command Shape

```bash
<chosen houmao-mgr launcher> mailbox unregister --address <address> [--mailbox-root <root>] [--mode deactivate|purge]
<chosen houmao-mgr launcher> project mailbox unregister --address <address> [--mode deactivate|purge]
```

## Guardrails

- Do not reinterpret deregistration as mailbox-root cleanup.
- Do not guess whether the user wants `deactivate` or `purge` when they expressed a retention preference.
