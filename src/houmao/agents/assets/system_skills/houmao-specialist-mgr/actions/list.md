# List Specialists Or Easy Profiles

Use this action only when the user wants to list persisted easy specialists or persisted easy profiles in the current project overlay.

## Workflow

1. Determine whether the user wants `specialists`, `profiles`, or both.
2. If that target list kind is still ambiguous after checking the prompt and recent chat context, ask the user before proceeding.
3. Use the `houmao-mgr` launcher already chosen by the top-level skill.
4. Run the matching list command.
5. Report the listed specialists or profiles from the command output.

## Command Shape

Use one of:

```text
<chosen houmao-mgr launcher> project easy specialist list
<chosen houmao-mgr launcher> project easy profile list
```

## Guardrails

- Do not ask for a specialist or profile name when the task is only to list resources.
- Do not mix this action with easy-instance listing or managed-agent listing.
- Do not infer or filter the result unless the user explicitly asks for extra selection after listing.
