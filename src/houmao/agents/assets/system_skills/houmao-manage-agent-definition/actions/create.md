# Create Definition

Use this action only when the user wants to create one new low-level role or one named preset.

## Workflow

1. Use the launcher resolved from the top-level skill.
2. Determine whether the target is a role or a preset.
3. Recover required inputs from the current prompt first and recent chat context second when they were stated explicitly.
4. If the target kind is still missing, ask the user in Markdown before proceeding. Prefer a compact table when the target kind or several required create inputs need clarification.
5. For one new role, require the role name. Include an initial prompt only when the user explicitly provided prompt text or a prompt file.
6. For one new preset, require the preset name, role name, and tool. Include optional `--setup`, `--auth`, repeatable `--skill`, and `--prompt-mode` only when the user explicitly asked for them.
7. Run the matching maintained command.
8. Report the created role or preset details returned by the command.

## Command Shapes

Use one of these maintained command shapes:

```text
<resolved houmao-mgr launcher> project agents roles init --name <role> [--system-prompt <text> | --system-prompt-file <path>]
<resolved houmao-mgr launcher> project agents presets add --name <preset> --role <role> --tool <tool> [--setup <name>] [--auth <bundle>] [--skill <name> ...] [--prompt-mode unattended|as_is]
```

## Guardrails

- Do not guess whether the user wanted a role or a preset.
- Do not guess the role name, preset name, tool lane, or prompt content.
- Do not use `project agents roles scaffold`.
- Do not replace this action with direct filesystem edits under `.houmao/agents/`.
