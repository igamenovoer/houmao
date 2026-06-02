# Low-Level Roles

Use this subskill when the user wants to create, inspect, update, list, or remove one prompt-only role through `internals native-agent roles ...`.

## Preconditions

- Read [../common/launcher.md](../common/launcher.md).
- Read [../common/missing-inputs.md](../common/missing-inputs.md).
- Confirm the target is a low-level role, not an specialist.

## Actions

- List: no role name required.
- Get: require `--name`; add `--include-prompt` only when the user asked for prompt text or the full role definition.
- Init: require `--name`; include prompt text or prompt file only when provided.
- Set: require `--name` and exactly one prompt mutation.
- Remove: require `--name`.

## Command Shapes

```text
<chosen houmao-mgr launcher> internals native-agent roles list
<chosen houmao-mgr launcher> internals native-agent roles get --name <role> [--include-prompt]
<chosen houmao-mgr launcher> internals native-agent roles remove --name <role>
```

For `init` and `set`, run the direct command with only explicit prompt fields:

```bash
<chosen houmao-mgr launcher> internals native-agent roles init --name <role> [--system-prompt <text> | --system-prompt-file <path>]
<chosen houmao-mgr launcher> internals native-agent roles set --name <role> [--system-prompt <text> | --system-prompt-file <path> | --clear-system-prompt]
```

## Guardrails

- Do not use `internals native-agent roles scaffold`.
- Do not use `internals native-agent roles presets ...`.
- Do not guess prompt text.
- Do not hand-edit `.houmao/agents/roles/`.
- Do not use roles when the user asked for a specialist template with credentials, skills, setup, model, or env defaults.
- Do not include prompt mutation flags unless the user supplied the prompt text, prompt file, or explicit clear request.
