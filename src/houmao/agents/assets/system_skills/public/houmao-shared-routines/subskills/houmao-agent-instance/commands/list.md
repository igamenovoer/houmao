# List Agent Instances

Use this action only when the user wants to list current live managed-agent instances.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Run `agents global list`.
3. Report the listed managed agents from the command output.


If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.
## Command Shape

Use:

```text
<chosen houmao-mgr launcher> agents global list
```

## Guardrails

- Do not ask for an agent name when the task is only to list managed agents.
- Do not route this action through `project agents list`.
- Do not filter or reinterpret the list unless the user explicitly asks for additional selection after listing.
