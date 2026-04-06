# Get Specialist

Use this action only when the user wants to inspect one persisted easy specialist definition.

## Workflow

1. Use the launcher resolved from the top-level skill.
2. Recover the specialist name from the current prompt first and recent chat context second when it was stated explicitly.
3. If the specialist name is still missing, ask the user in Markdown before proceeding. Prefer a short bullet list when you only need the specialist name.
4. Run `project easy specialist get --name <name>`.
5. Report the specialist details returned by the command.

## Command Shape

Use:

```text
<resolved houmao-mgr launcher> project easy specialist get --name <name>
```

## Guardrails

- Do not guess which persisted specialist the user meant.
- Do not inspect or fetch a specialist from partial name inference when the prompt and recent chat context do not identify it explicitly.
- Do not treat easy-instance names as interchangeable with specialist names.
- Do not enter credential discovery or specialist-authoring flow for this action.
