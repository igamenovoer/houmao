# Get Definition

Use this action only when the user wants to inspect one low-level role or one named recipe.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Determine whether the target is a role or a recipe.
3. Recover the target name from the current prompt first and recent chat context second when it was stated explicitly.
4. If the target kind or target name is still missing, ask the user in Markdown before proceeding. Prefer a short bullet list when you only need one or two fields.
5. For one role:
   - run `project agents roles get --name <role>` for summary-oriented inspection
   - add `--include-prompt` only when the user explicitly asked for prompt text or the full low-level role definition
6. For one recipe, run `project agents recipes get --name <recipe>`.
7. If the user asks to inspect env vars or auth files inside one auth bundle, stop and route that request to `houmao-credential-mgr`.
8. Report the returned role or recipe details.

## Command Shapes

Use one of these maintained command shapes:

```text
<chosen houmao-mgr launcher> project agents roles get --name <role>
<chosen houmao-mgr launcher> project agents roles get --name <role> --include-prompt
<chosen houmao-mgr launcher> project agents recipes get --name <recipe>
```

## Guardrails

- Do not guess whether the user wanted a role or a recipe.
- Do not add `--include-prompt` unless the user explicitly asked for prompt text or the full low-level role definition.
- Do not bypass `roles get --include-prompt` by reading `.houmao/agents/roles/<role>/system-prompt.md` directly.
- Do not treat auth-bundle content inspection as part of this skill.
