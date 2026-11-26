# List Agent Instances

Use this action when the user wants to list current live managed-agent instances or locally registered external communication-only agent imports.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Run `agents global list` for live local managed-agent instances, and run `agents external list` when the request includes or targets locally registered external communication-only agent records.
3. Report the listed local managed instances and any external communication-only imports separately from the command output.

If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.

## Command Shape

```text
<chosen houmao-mgr launcher> agents global list
<chosen houmao-mgr launcher> agents external list
```

## Guardrails

- DO NOT ask for an agent name when the task is only to list managed or external agents.
- DO NOT route this action through `project agents list`.
- DO NOT present `agents external list` records as locally runtime-controllable instances (`launch`, `stop`, `relaunch`, or `join`).
- DO NOT filter or reinterpret the list unless the user explicitly asks for additional selection after listing.
