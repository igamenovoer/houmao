# List Definitions

Use this action only when the user wants to list low-level roles or named presets.

## Workflow

1. Use the launcher resolved from the top-level skill.
2. Determine whether the user wants roles or presets.
3. Recover any explicit preset filters from the current prompt first and recent chat context second when they were stated explicitly.
4. If the target kind is still missing, ask the user in Markdown before proceeding. Prefer a short bullet list when you only need the target kind.
5. Run `project agents roles list` for roles.
6. Run `project agents presets list` for presets, adding `--role` or `--tool` only when the user explicitly asked for those filters.
7. Report the returned list.

## Command Shapes

Use one of these maintained command shapes:

```text
<resolved houmao-mgr launcher> project agents roles list
<resolved houmao-mgr launcher> project agents presets list [--role <role>] [--tool <tool>]
```

## Guardrails

- Do not guess whether the user wanted a role list or a preset list.
- Do not add preset filters the user did not ask for explicitly.
- Do not use `project agents roles presets ...`.
