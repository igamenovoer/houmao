# Low-Level Roles

Use this subskill when the user wants to create, inspect, update, list, or remove one prompt-only role through `project agents roles ...`.

## Preconditions

- Read [../common/launcher.md](../common/launcher.md).
- Read [../common/missing-inputs.md](../common/missing-inputs.md).
- Confirm the target is a low-level role, not an easy specialist.

## Actions

- List: no role name required.
- Get: require `--name`; add `--include-prompt` only when the user asked for prompt text or the full role definition.
- Init: require `--name`; include prompt text or prompt file only when provided.
- Set: require `--name` and exactly one prompt mutation.
- Remove: require `--name`.

## Command Shapes

```text
<chosen houmao-mgr launcher> project agents roles list
<chosen houmao-mgr launcher> project agents roles get --name <role> [--include-prompt]
<chosen houmao-mgr launcher> project agents roles remove --name <role>
```

For `init` and `set`, use the CLI-owned templates:

- `project.agents.roles.init`
- `project.agents.roles.set`

Render sparse intent before running the target command:

```text
<chosen houmao-mgr launcher> --print-json internals command-templates render --id project.agents.roles.init --intent '<json>'
```

## Guardrails

- Do not use `project agents roles scaffold`.
- Do not use `project agents roles presets ...`.
- Do not guess prompt text.
- Do not hand-edit `.houmao/agents/roles/`.
- Do not use roles when the user asked for a specialist template with credentials, skills, setup, model, or env defaults.
- Do not hand-author covered role init or set commands from Markdown skeletons.
