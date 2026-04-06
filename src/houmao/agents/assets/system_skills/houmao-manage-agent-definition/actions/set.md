# Set Definition

Use this action only when the user wants to update one existing low-level role or one named preset.

## Workflow

1. Use the launcher resolved from the top-level skill.
2. Determine whether the target is a role or a preset.
3. Recover the target name and explicit mutations from the current prompt first and recent chat context second when they were stated explicitly.
4. If the target kind, target name, or required explicit mutation is still missing, ask the user in Markdown before proceeding.
5. For one role, require at least one explicit prompt mutation and run `project agents roles set --name <role>` with exactly one of:
   - `--system-prompt <text>`
   - `--system-prompt-file <path>`
   - `--clear-system-prompt`
6. For one preset, require at least one explicit preset mutation and run `project agents presets set --name <preset>` with only the requested supported flags:
   - `--role <role>`
   - `--tool <tool>`
   - `--setup <setup>`
   - `--auth <bundle>` or `--clear-auth`
   - `--add-skill <skill>`
   - `--remove-skill <skill>`
   - `--clear-skills`
   - `--prompt-mode unattended|as_is` or `--clear-prompt-mode`
7. Treat changing which credential bundle one preset references as a preset-structure update through `project agents presets set --auth ...` or `--clear-auth`.
8. If the user asks to mutate env vars or auth files inside the bundle itself, stop and route that request to `houmao-manage-credentials`.
9. Report the updated role or preset details returned by the command.

## Command Shapes

Use one of these maintained command shapes:

```text
<resolved houmao-mgr launcher> project agents roles set --name <role> [--system-prompt <text> | --system-prompt-file <path> | --clear-system-prompt]
<resolved houmao-mgr launcher> project agents presets set --name <preset> [--role <role>] [--tool <tool>] [--setup <setup>] [--auth <bundle> | --clear-auth] [--add-skill <skill> ...] [--remove-skill <skill> ...] [--clear-skills] [--prompt-mode unattended|as_is | --clear-prompt-mode]
```

## Guardrails

- Do not continue when the user has not provided any explicit supported role or preset change.
- Do not treat auth-bundle content mutation as a preset-definition change; use `houmao-manage-credentials`.
- Do not invent unsupported preset mutation flags.
- Do not use `project agents roles presets ...`.
