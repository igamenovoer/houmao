# List Specialists

Use this action only when the user wants to list persisted easy specialists in the current project overlay.

## Workflow

1. Use the launcher resolved from the top-level skill.
2. Run `project easy specialist list`.
3. Report the listed specialists from the command output.

## Command Shape

Use:

```text
<resolved houmao-mgr launcher> project easy specialist list
```

## Guardrails

- Do not ask for a specialist name when the task is only to list specialists.
- Do not mix this action with easy-instance listing or managed-agent listing.
- Do not infer or filter the result unless the user explicitly asks for extra selection after listing.
