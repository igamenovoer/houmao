# List Definitions

Use this action only when the user wants to list low-level roles or named recipes.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Determine whether the user wants roles or recipes.
3. Recover any explicit recipe filters from the current prompt first and recent chat context second when they were stated explicitly.
4. If the target kind is still missing, ask the user in Markdown before proceeding. Prefer a short bullet list when you only need the target kind.
5. Run `project agents roles list` for roles.
6. Run `project agents recipes list` for recipes, adding `--role` or `--tool` only when the user explicitly asked for those filters.
7. Report the returned list.

## Command Shapes

Use one of these maintained command shapes:

```text
<chosen houmao-mgr launcher> project agents roles list
<chosen houmao-mgr launcher> project agents recipes list [--role <role>] [--tool <tool>]
```

## Guardrails

- Do not guess whether the user wanted a role list or a recipe list.
- Do not add recipe filters the user did not ask for explicitly.
- Do not use `project agents roles presets ...`.
