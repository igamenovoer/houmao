# Inspect Late Managed-Agent Mailbox Binding

Use this action only when the user wants late filesystem mailbox posture for one existing local managed agent.

## Workflow

1. Require one managed-agent selector: `--agent-id` or `--agent-name`.
2. Use the `houmao-mgr` launcher already chosen by the top-level skill.
3. Run the managed-agent mailbox status command.
4. Report the late mailbox binding posture for that managed agent.

## Template Rendering

Use this template id, then run the rendered `argv`:

```text
agents.mailbox.status
```

## Guardrails

- Do not use mailbox-root actions when the task is only existing-agent binding status.
- Do not reinterpret this action as generic managed-agent lifecycle work.
