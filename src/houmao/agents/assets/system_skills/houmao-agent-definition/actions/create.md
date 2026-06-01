# Create Definition

Legacy low-level-only action reference. Current routing should use the `roles` or `recipes` subcommands from `../SKILL.md`.

Use this action only when the user wants to create one new low-level role or one named recipe.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Determine whether the target is a role or a recipe.
3. Recover required inputs from the current prompt first and recent chat context second when they were stated explicitly.
4. If the target kind is still missing, ask the user in Markdown before proceeding. Follow `subskills/common/missing-inputs.md` so `Required` and `Optional` inputs are separate.
5. For one new role, require the role name. Include an initial prompt only when the user explicitly provided prompt text or a prompt file.
6. For one new recipe, require the recipe name, role name, and tool. Include optional `--setup`, `--auth`, repeatable `--skill`, and `--prompt-mode` only when the user explicitly asked for them.
7. Render the matching CLI-owned template, then run the rendered `argv`.
8. Report the created role or recipe details returned by the command.

## Template Rendering

Use one of these template ids:

```text
project.agents.roles.init
project.agents.recipes.add
```

## Guardrails

- Do not guess whether the user wanted a role or a recipe.
- Do not guess the role name, recipe name, tool lane, or prompt content.
- Do not use `project agents roles scaffold`.
- Do not replace this action with direct filesystem edits under `.houmao/agents/`.
