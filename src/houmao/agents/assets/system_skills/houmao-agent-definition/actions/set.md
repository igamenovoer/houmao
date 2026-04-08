# Set Definition

Use this action only when the user wants to update one existing low-level role or one named recipe.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Determine whether the target is a role or a recipe.
3. Recover the target name and explicit mutations from the current prompt first and recent chat context second when they were stated explicitly.
4. If the target kind, target name, or required explicit mutation is still missing, ask the user in Markdown before proceeding.
5. For one role, require at least one explicit prompt mutation and run `project agents roles set --name <role>` with exactly one of:
   - `--system-prompt <text>`
   - `--system-prompt-file <path>`
   - `--clear-system-prompt`
6. For one recipe, require at least one explicit recipe mutation and run `project agents recipes set --name <recipe>` with only the requested supported flags:
   - `--role <role>`
   - `--tool <tool>`
   - `--setup <setup>`
   - `--auth <bundle>` or `--clear-auth`
   - `--add-skill <skill>`
   - `--remove-skill <skill>`
   - `--clear-skills`
   - `--prompt-mode unattended|as_is` or `--clear-prompt-mode`
7. Treat changing which credential bundle one recipe references as a recipe-structure update through `project agents recipes set --auth ...` or `--clear-auth`.
8. If the user asks to mutate env vars or auth files inside the bundle itself, stop and route that request to `houmao-credential-mgr`.
9. Report the updated role or recipe details returned by the command.

## Command Shapes

Use one of these maintained command shapes:

```text
<chosen houmao-mgr launcher> project agents roles set --name <role> [--system-prompt <text> | --system-prompt-file <path> | --clear-system-prompt]
<chosen houmao-mgr launcher> project agents recipes set --name <recipe> [--role <role>] [--tool <tool>] [--setup <setup>] [--auth <bundle> | --clear-auth] [--add-skill <skill> ...] [--remove-skill <skill> ...] [--clear-skills] [--prompt-mode unattended|as_is | --clear-prompt-mode]
```

## Guardrails

- Do not continue when the user has not provided any explicit supported role or recipe change.
- Do not treat auth-bundle content mutation as a recipe-definition change; use `houmao-credential-mgr`.
- Do not invent unsupported recipe mutation flags.
- Do not use `project agents roles presets ...`.
