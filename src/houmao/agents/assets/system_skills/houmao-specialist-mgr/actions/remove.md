# Remove Specialist Or Easy Profile

Use this action only when the user wants to remove one persisted easy specialist definition or one persisted easy profile.

## Workflow

1. Determine whether the target resource is `specialist` or `profile`.
2. If that target resource kind is still ambiguous after checking the prompt and recent chat context, ask the user before proceeding.
3. Use the `houmao-mgr` launcher already chosen by the top-level skill.
4. Recover the specialist or profile name from the current prompt first and recent chat context second when it was stated explicitly.
5. If the target name is still missing, ask the user in Markdown before proceeding. Prefer a short bullet list when you only need the name.
6. Run the matching remove command.
7. Report the removed specialist or profile plus the returned preserved-path metadata when present.

## Command Shape

Use one of:

```text
<chosen houmao-mgr launcher> project easy specialist remove --name <name>
<chosen houmao-mgr launcher> project easy profile remove --name <name>
```

## Guardrails

- Do not guess which persisted specialist or profile to remove.
- Do not remove a specialist or profile from partial name inference when the prompt and recent chat context do not identify it explicitly.
- Do not remove multiple specialists or profiles unless the user explicitly asks for that broader operation.
- Do not present specialist removal as deleting the shared auth bundle or imported skills automatically; report the preserved auth and skill paths returned by the command.
- Do not imply that removing an easy profile also removes its referenced specialist.
- Do not route easy-instance stop or runtime cleanup work through this action.
