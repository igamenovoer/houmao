# Create Definition

Legacy low-level-only action reference. Current routing should use the `roles` or `recipes` subcommands from `../SKILL-MAIN.md`.

Use this action only when the user wants to create one new low-level role or one named recipe.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Determine whether the target is a role or a recipe.
3. Recover required inputs from the current prompt first and recent chat context second when they were stated explicitly.
4. If the target kind is still missing, ask the user in Markdown before proceeding. Follow `references/common/missing-inputs.md` so `Required` and `Optional` inputs are separate.
5. For one new role, require the role name. Include an initial prompt only when the user explicitly provided prompt text or a prompt file.
6. For one new recipe, require the recipe name, role name, and tool. Include optional `--setup`, `--auth`, repeatable `--skill`, and `--prompt-mode` only when the user explicitly asked for them.
7. Run the matching direct command with only explicit fields.
8. Report the created role or recipe details returned by the command.

## Command Shape

```bash
<chosen houmao-mgr launcher> internals native-agent roles init --name <role> [--system-prompt <text> | --system-prompt-file <path>]
<chosen houmao-mgr launcher> internals native-agent recipes add --name <recipe> --role <role> --tool <tool> [--setup <setup>] [--auth <auth>] [--skill <skill>] [--prompt-mode unattended|as_is]
```

## Guardrails

- Do not guess whether the user wanted a role or a recipe.
- Do not guess the role name, recipe name, tool lane, or prompt content.
- Do not use `internals native-agent roles scaffold`.
- Do not replace this action with direct filesystem edits under `.houmao/agents/`.
