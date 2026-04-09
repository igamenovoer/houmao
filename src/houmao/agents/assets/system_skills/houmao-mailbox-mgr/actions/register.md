# Register A Mailbox Account

Use this action only when the user wants to create or reuse one manually administered filesystem mailbox registration under one mailbox root.

## Workflow

1. Determine whether the task targets one arbitrary filesystem mailbox root or the active project mailbox root.
2. Confirm that manual mailbox-account registration is actually the right lane:
   - for an already-running local managed agent, use the late-binding action pages instead
   - for a new specialist-backed easy instance whose ordinary mailbox address will be derived from the managed-agent name under the same shared root, explain that the later launch step may own mailbox registration instead of preregistering that address here
3. Require the full mailbox address and mailbox owner principal id.
4. If the user asks how to choose those values, explain the ordinary split explicitly: principal id `HOUMAO-<agentname>`, mailbox address `<agentname>@houmao.localhost`, and reserved `HOUMAO-*` mailbox local parts under `houmao.localhost` for Houmao-owned system principals only.
5. If the user supplied a registration mode, preserve it exactly; otherwise let the command default to `safe`.
6. Use the `houmao-mgr` launcher already chosen by the top-level skill.
7. Run the matching mailbox registration command.
8. Report the returned registration payload, including replacement posture when relevant.

## Command Shape

Use one of:

```text
<chosen houmao-mgr launcher> mailbox register --address <full-address> --principal-id <principal-id> [--mailbox-root <path>] [--mode safe|force|stash] [--yes]
<chosen houmao-mgr launcher> project mailbox register --address <full-address> --principal-id <principal-id> [--mode safe|force|stash] [--yes]
```

## Guardrails

- Do not guess the mailbox address or principal id.
- Do not recommend `HOUMAO-<agentname>@houmao.localhost` as the ordinary mailbox-address pattern.
- Do not present this action as the default way to prepare per-agent mailbox addresses that a same-root `project easy instance launch --mail-transport filesystem --mail-root ...` step can own later.
- Do not skip the overwrite-confirmation contract when the task is destructive and non-interactive.
- Do not treat registration as a direct agent-binding task; use the late-binding action pages for existing managed agents.
