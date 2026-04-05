# Remove Specialist

Use this action only when the user wants to remove one persisted easy specialist definition.

## Workflow

1. Use the launcher resolved from the top-level skill.
2. Recover the specialist name from the current prompt first and recent chat context second when it was stated explicitly.
3. If the specialist name is still missing, ask the user before proceeding.
4. Run `project easy specialist remove --name <name>`.
5. Report the removed specialist name plus the preserved auth and skill paths returned by the command.

## Command Shape

Use:

```text
<resolved houmao-mgr launcher> project easy specialist remove --name <name>
```

## Guardrails

- Do not guess which persisted specialist to remove.
- Do not remove multiple specialists unless the user explicitly asks for that broader operation.
- Do not present removal as deleting the shared auth bundle or imported skills automatically; report the preserved auth and skill paths returned by the command.
- Do not route easy-instance stop or runtime cleanup work through this action.
