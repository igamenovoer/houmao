# List Definitions

Legacy low-level-only action reference. Current routing should use the `roles` or `recipes` subcommands from `../SKILL.md`.

Use this action only when the user wants to list low-level roles or named recipes.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Determine whether the user wants roles or recipes.
3. Recover any explicit recipe filters from the current prompt first and recent chat context second when they were stated explicitly.
4. If the target kind is still missing, ask the user in Markdown before proceeding. Follow `subskills/common/missing-inputs.md` so `Required` and `Optional` inputs are separate.
5. Run `internals native-agent roles list` for roles.
6. Run `internals native-agent recipes list` for recipes, adding `--role` or `--tool` only when the user explicitly asked for those filters.
7. Report the returned list.

## Command Shapes

Use one of these maintained command shapes:

```text
<chosen houmao-mgr launcher> internals native-agent roles list
<chosen houmao-mgr launcher> internals native-agent recipes list [--role <role>] [--tool <tool>]
```

## Guardrails

- Do not guess whether the user wanted a role list or a recipe list.
- Do not add recipe filters the user did not ask for explicitly.
- Do not use `internals native-agent roles presets ...`.
