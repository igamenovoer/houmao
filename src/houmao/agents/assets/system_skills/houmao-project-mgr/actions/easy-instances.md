# Inspect Or Stop Easy Instances Through The Selected Overlay

Use this action only when the user wants to list, inspect, or stop easy instances through the selected project overlay.

## Workflow

1. Determine whether the user wants to `list`, `get`, or `stop` one easy instance.
2. Recover the instance name from the prompt or recent chat context when it was stated explicitly.
3. If the action or required instance name is still missing, ask before proceeding.
4. Use the `houmao-mgr` launcher already chosen by the top-level skill.
5. Run the matching easy-instance command.
6. Report the selected overlay details and the instance result from the command output.

## Command Shape

Use one of:

```text
<chosen houmao-mgr launcher> project easy instance list
<chosen houmao-mgr launcher> project easy instance get --name <name>
<chosen houmao-mgr launcher> project easy instance stop --name <name>
```

## Behavior Notes

- These commands use non-creating selected-overlay resolution and therefore require an already-existing selected project overlay.
- `get` and `stop` verify that the managed agent belongs to the selected overlay.
- Specialist-backed or profile-backed easy `launch` remains on `houmao-specialist-mgr`.

## Guardrails

- Do not guess an instance name for `get` or `stop`.
- Do not route easy-instance `launch` through this action.
- Do not present these commands as the canonical generic lifecycle surface after the user leaves the project-scoped inspection or stop task; broader live-agent lifecycle belongs to `houmao-agent-instance`.
