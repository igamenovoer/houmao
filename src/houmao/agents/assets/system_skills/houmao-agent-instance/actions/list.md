# List Agent Instances

Use this action only when the user wants to list current live managed-agent instances.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Run `agents list`.
3. Report the listed managed agents from the command output.

## Command Shape

Use:

```text
<chosen houmao-mgr launcher> agents list
```

## Guardrails

- Do not ask for an agent name when the task is only to list managed agents.
- Do not route this action through `project easy instance list`.
- Do not filter or reinterpret the list unless the user explicitly asks for additional selection after listing.
