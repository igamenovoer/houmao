---
skill_invocation_notation: >
  Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
  SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
  accepted only as legacy input when SKILL-MAIN.md is absent.
  Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
  `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
  `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
  subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
  by parent subcommand parent. Intermediate subcommands act as object generators.
  Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints.
---

# Set Definition

Legacy low-level-only action reference. Current routing should use the `roles` or `recipes` subcommands from `../SKILL-MAIN.md`.

Use this action only when the user wants to update one existing low-level role or one named recipe.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Determine whether the target is a role or a recipe.
3. Recover the target name and explicit mutations from the current prompt first and recent chat context second when they were stated explicitly.
4. If the target kind, target name, or required explicit mutation is still missing, ask the user in Markdown before proceeding. Follow `references/common/missing-inputs.md` so `Required` and `Optional` inputs are separate.
5. For one role, require at least one explicit prompt mutation and run `internals native-agent roles set` with exactly one of:
   - `--system-prompt <text>`
   - `--system-prompt-file <path>`
   - `--clear-system-prompt`
6. For one recipe, require at least one explicit recipe mutation and run `internals native-agent recipes set` with only the requested supported fields:
   - `--role <role>`
   - `--tool <tool>`
   - `--setup <setup>`
   - `--auth <bundle>` or `--clear-auth`
   - `--add-skill <skill>`
   - `--remove-skill <skill>`
   - `--clear-skills`
   - `--prompt-mode unattended|as_is` or `--clear-prompt-mode`
7. Treat changing which credential bundle one recipe references as a recipe-structure update through `internals native-agent recipes set --auth ...` or `--clear-auth`.
8. If the user asks to mutate env vars or auth files inside the bundle itself, stop and route that request to `houmao-shared-routines->houmao-credential-mgr`.
9. Report the updated role or recipe details returned by the command.


If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.
## Command Shape

```bash
<chosen houmao-mgr launcher> internals native-agent roles set --name <role> [--system-prompt <text> | --system-prompt-file <path> | --clear-system-prompt]
<chosen houmao-mgr launcher> internals native-agent recipes set --name <recipe> [--role <role>] [--tool <tool>] [--setup <setup>] [--auth <bundle> | --clear-auth] [--add-skill <skill>] [--remove-skill <skill>] [--clear-skills] [--prompt-mode unattended|as_is | --clear-prompt-mode]
```

## Guardrails

- Do not continue when the user has not provided any explicit supported role or recipe change.
- Do not treat auth-bundle content mutation as a recipe-definition change; use `houmao-shared-routines->houmao-credential-mgr`.
- Do not invent unsupported recipe mutation flags.
- Do not use `internals native-agent roles presets ...`.
