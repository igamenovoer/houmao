# Login Credential

Use this action only when the user wants to run a provider login flow for a fresh Claude or Codex account and import the resulting auth file into Houmao credential storage. Kimi credential CRUD is supported by the other action pages, but Kimi does not have a maintained Houmao credential login helper.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the tool family, credential name, target, and whether this is a create or explicit update from the current prompt first and recent chat context second when they were stated explicitly.
3. If the selected tool is `kimi`, stop and explain that Kimi credential login helper workflow is not maintained; route Kimi credential creation or updates through `actions/add.md` or `actions/set.md` with explicit Kimi credential inputs instead.
4. If the tool family, credential name, or target is still missing, ask the user before proceeding.
5. Use the default create-only login behavior unless the user explicitly said to update, replace, or refresh an existing credential.
6. Build the direct command: `project credentials <tool> login` for the project lane or `internals native-agent credentials <tool> login` for the direct native-agent lane.
7. Run the direct command and let the user complete any provider browser, device-code, console, or paste-back authentication steps.
8. Report the credential name, provider command, and temp-home cleanup status returned by the command.

## Required Inputs

- `tool`: one of `claude` or `codex`
- `name`
- a resolved target

## Command Shape

Run the matching direct command:

```bash
<chosen houmao-mgr launcher> project credentials <tool> login --name <credential> [--update]
<chosen houmao-mgr launcher> internals native-agent credentials <tool> login --native-agent-root <dir> --name <credential> [--update]
```

Add `--update` only when the user explicitly intends to replace an existing credential.

## Guardrails

- Do not guess the tool family, target, or credential name.
- Do not run or invent a Kimi login helper; Kimi does not have one in this change.
- Do not add `--update` unless the user explicitly asked to update, replace, or refresh an existing credential.
- Do not manually create provider home directories, run provider login commands, copy auth files into Houmao storage, or delete temp directories for this ordinary workflow.
- Do not scan existing provider homes to infer the account unless the user explicitly asks for a lower-level recovery workflow.
- If the command fails and reports a preserved temp home, report that path as recovery context instead of deleting it yourself.
