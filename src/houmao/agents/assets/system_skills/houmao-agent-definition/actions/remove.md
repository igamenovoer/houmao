# Remove Definition

Use this action only when the user wants to remove one low-level role or one named recipe.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Determine whether the target is a role or a recipe.
3. Recover the concrete target name from the current prompt first and recent chat context second when it was stated explicitly.
4. If the target kind or target name is still missing, ask the user in Markdown before proceeding. Prefer a short bullet list when you only need one or two fields.
5. Run `project agents roles remove --name <role>` for one role.
6. Run `project agents recipes remove --name <recipe>` for one recipe.
7. Report the removal result. If role removal is blocked because recipes still reference that role, report the CLI error instead of editing files manually.

## Command Shapes

Use one of these maintained command shapes:

```text
<chosen houmao-mgr launcher> project agents roles remove --name <role>
<chosen houmao-mgr launcher> project agents recipes remove --name <recipe>
```

## Guardrails

- Do not guess whether the user wanted a role or a recipe removed.
- Do not guess the target name.
- Do not bypass CLI safety checks by deleting `.houmao/agents/` files directly.
