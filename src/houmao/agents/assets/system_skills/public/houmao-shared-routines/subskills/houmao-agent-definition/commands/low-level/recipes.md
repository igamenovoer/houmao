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

# Low-Level Recipes

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

Use this subskill when the user wants to create, inspect, update, list, or remove one low-level recipe through `internals native-agent recipes ...`.

## Preconditions

- Read [../../references/common/launcher.md](../../references/common/launcher.md).
- Read [../../references/common/missing-inputs.md](../../references/common/missing-inputs.md).
- Read [../../references/common/credential-routing.md](../../references/common/credential-routing.md) when auth references are involved.
- Confirm the target is a recipe, not an specialist or project profile.

## Actions

- List: no recipe name required.
- Get: require `--name`.
- Add: require recipe name, role name, and tool.
- Set: require recipe name and at least one supported mutation.
- Remove: require recipe name.

## Command Shapes

```text
<chosen houmao-mgr launcher> internals native-agent recipes list
<chosen houmao-mgr launcher> internals native-agent recipes get --name <recipe>
<chosen houmao-mgr launcher> internals native-agent recipes remove --name <recipe>
```

For `add` and `set`, run the direct command with only explicit recipe fields:

```bash
<chosen houmao-mgr launcher> internals native-agent recipes add --name <recipe> --role <role> --tool <tool> [--setup <setup>] [--auth <auth>] [--skill <skill>] [--prompt-mode unattended|as_is]
<chosen houmao-mgr launcher> internals native-agent recipes set --name <recipe> [--role <role>] [--tool <tool>] [--setup <setup>] [--auth <auth> | --clear-auth] [--add-skill <skill>] [--remove-skill <skill>] [--clear-skills] [--prompt-mode unattended|as_is | --clear-prompt-mode]
```

## Guardrails

- Do not guess the role, recipe name, tool, setup, auth bundle, skills, or prompt mode.
- Do not treat auth-bundle content mutation as recipe authoring; use `houmao-shared-routines->houmao-credential-mgr`.
- Do not remove and recreate a recipe for ordinary edits.
- Do not hand-edit `.houmao/agents/presets/`.
- Do not add `--prompt-mode` by default; include it only when prompt mode is explicit.
