# Low-Level Roles

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

Use this subskill when the user wants to create, inspect, update, list, or remove one prompt-only role through `internals native-agent roles ...`.

## Preconditions

- Read [../../references/common/launcher.md](../../references/common/launcher.md).
- Read [../../references/common/missing-inputs.md](../../references/common/missing-inputs.md).
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
