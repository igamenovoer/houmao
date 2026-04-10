# Register Late Managed-Agent Mailbox Binding

Use this action only when the user wants to add or update one filesystem mailbox binding on an existing local managed agent without relaunch.

## Workflow

1. Require one managed-agent selector: `--agent-id` or `--agent-name`.
2. Preserve explicit mailbox-root, principal-id, address, mode, or overwrite-confirmation inputs when the user supplied them.
3. When the user asks what omitted mailbox identity values will become, explain that the ordinary managed-agent defaults are principal id `HOUMAO-<agentname>` and mailbox address `<agentname>@houmao.localhost`, and that `HOUMAO-*` mailbox local parts under `houmao.localhost` are reserved for Houmao-owned system principals.
4. Use the `houmao-mgr` launcher already chosen by the top-level skill.
5. Run the late mailbox-binding registration command.
6. Report the resulting binding payload and any replacement posture that mattered.

## Command Shape

Use:

```text
<chosen houmao-mgr launcher> agents mailbox register (--agent-id <id> | --agent-name <name>) [--mailbox-root <path>] [--principal-id <principal-id>] [--address <full-address>] [--mode safe|force|stash] [--yes]
```

## Guardrails

- Do not ask for `--principal-id` or `--address` when the managed-agent identity defaults already satisfy the task and the user did not request overrides.
- Do not describe the ordinary late-binding default mailbox address as `HOUMAO-<agentname>@houmao.localhost`.
- Do not use this action to create or validate the mailbox root itself; use the mailbox-root actions first when root lifecycle work is still missing.
- Do not require relaunch for supported local managed-agent late binding.
