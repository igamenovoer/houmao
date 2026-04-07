# Get Specialist Or Easy Profile

Use this action only when the user wants to inspect one persisted easy specialist definition or one persisted easy profile.

## Workflow

1. Determine whether the target resource is `specialist` or `profile`.
2. If that target resource kind is still ambiguous after checking the prompt and recent chat context, ask the user before proceeding.
3. Use the launcher resolved from the top-level skill.
4. Recover the specialist or profile name from the current prompt first and recent chat context second when it was stated explicitly.
5. If the target name is still missing, ask the user in Markdown before proceeding. Prefer a short bullet list when you only need the name.
6. Run the matching get command.
7. Report the specialist or profile details returned by the command.

## Command Shape

Use one of:

```text
<resolved houmao-mgr launcher> project easy specialist get --name <name>
<resolved houmao-mgr launcher> project easy profile get --name <name>
```

## Guardrails

- Do not guess which persisted specialist or profile the user meant.
- Do not inspect or fetch a specialist or profile from partial name inference when the prompt and recent chat context do not identify it explicitly.
- Do not treat easy-instance names as interchangeable with specialist names or profile names.
- Do not enter credential discovery or creation flow for this action.
