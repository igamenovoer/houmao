# Register A Mailbox Account

Use this action only when the user wants to create or reuse one filesystem mailbox registration under one mailbox root.

## Workflow

1. Determine whether the task targets one arbitrary filesystem mailbox root or the active project mailbox root.
2. Require the full mailbox address and mailbox owner principal id.
3. If the user supplied a registration mode, preserve it exactly; otherwise let the command default to `safe`.
4. Use the `houmao-mgr` launcher already chosen by the top-level skill.
5. Run the matching mailbox registration command.
6. Report the returned registration payload, including replacement posture when relevant.

## Command Shape

Use one of:

```text
<chosen houmao-mgr launcher> mailbox register --address <full-address> --principal-id <principal-id> [--mailbox-root <path>] [--mode safe|force|stash] [--yes]
<chosen houmao-mgr launcher> project mailbox register --address <full-address> --principal-id <principal-id> [--mode safe|force|stash] [--yes]
```

## Guardrails

- Do not guess the mailbox address or principal id.
- Do not skip the overwrite-confirmation contract when the task is destructive and non-interactive.
- Do not treat registration as a direct agent-binding task; use the late-binding action pages for existing managed agents.
