# Low-Level Recipes

Use this subskill when the user wants to create, inspect, update, list, or remove one low-level recipe through `project agents recipes ...`. `project agents presets ...` remains a compatibility alias for the same recipe resources.

## Preconditions

- Read [../common/launcher.md](../common/launcher.md).
- Read [../common/missing-inputs.md](../common/missing-inputs.md).
- Read [../common/credential-routing.md](../common/credential-routing.md) when auth references are involved.
- Confirm the target is a recipe, not an easy specialist or easy profile.

## Actions

- List: no recipe name required.
- Get: require `--name`.
- Add: require recipe name, role name, and tool.
- Set: require recipe name and at least one supported mutation.
- Remove: require recipe name.

## Command Shapes

```text
<chosen houmao-mgr launcher> project agents recipes list
<chosen houmao-mgr launcher> project agents recipes get --name <recipe>
<chosen houmao-mgr launcher> project agents recipes remove --name <recipe>
```

For `add` and `set`, use the CLI-owned templates:

- `project.agents.recipes.add`
- `project.agents.recipes.set`

Render sparse intent before running the target command:

```text
<chosen houmao-mgr launcher> --print-json internals command-templates render --id project.agents.recipes.add --intent '<json>'
```

## Preset Alias

Use `project agents presets ...` only when the user explicitly asks for the compatibility alias or an older context names presets. Prefer `recipes ...` for new guidance.

## Guardrails

- Do not guess the role, recipe name, tool, setup, auth bundle, skills, or prompt mode.
- Do not treat auth-bundle content mutation as recipe authoring; use `houmao-credential-mgr`.
- Do not remove and recreate a recipe for ordinary edits.
- Do not hand-edit `.houmao/agents/presets/`.
- Do not add `--prompt-mode` by default; render it only when prompt mode is explicit.
