# Unregister Late Managed-Agent Mailbox Binding

Use this action only when the user wants to remove one filesystem mailbox binding from an existing local managed agent without relaunch.

## Workflow

1. Require one managed-agent selector: `--agent-id` or `--agent-name`.
2. Preserve an explicit `deactivate` or `purge` mode when the user supplied one; otherwise let the command default to `deactivate`.
3. Use the `houmao-mgr` launcher already chosen by the top-level skill.
4. Run the late mailbox-binding deregistration command.
5. Report the resulting binding posture for that managed agent.

## Command Shape

Use:

```text
<chosen houmao-mgr launcher> agents mailbox unregister (--agent-id <id> | --agent-name <name>) [--mode deactivate|purge]
```

## Guardrails

- Do not reinterpret this action as mailbox-root cleanup or managed-agent stop.
- Do not require a mailbox-root override when the task is only existing-agent binding removal.
