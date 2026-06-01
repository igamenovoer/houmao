# Login Credential

Use this action only when the user wants to run a provider login flow for a fresh Claude, Codex, or Gemini account and import the resulting auth file into Houmao credential storage.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the tool family, credential name, target, and whether this is a create or explicit update from the current prompt first and recent chat context second when they were stated explicitly.
3. If the tool family, credential name, or target is still missing, ask the user before proceeding.
4. Use the default create-only login behavior unless the user explicitly said to update, replace, or refresh an existing credential.
5. Render the selected command template: `project.credentials.<tool>.login` for the project lane or `credentials.<tool>.login` for the plain agent-definition lane.
6. Run the rendered `argv` and let the user complete any provider browser, device-code, console, or paste-back authentication steps.
7. Report the credential name, provider command, and temp-home cleanup status returned by the command.

## Required Inputs

- `tool`: one of `claude`, `codex`, or `gemini`
- `name`
- a resolved target

## Command Shape

Use the matching CLI-owned template, then run its rendered `argv`:

```text
<chosen houmao-mgr launcher> --print-json internals command-templates render --id project.credentials.<tool>.login --intent '<json>'
<chosen houmao-mgr launcher> --print-json internals command-templates render --id credentials.<tool>.login --intent '<json>'
```

Use `show --id <template-id>` for authoritative login options. Render `update=true` only when the user explicitly intends to replace an existing credential.

## Guardrails

- Do not guess the tool family, target, or credential name.
- Do not add `--update` unless the user explicitly asked to update, replace, or refresh an existing credential.
- Do not manually create provider home directories, run provider login commands, copy auth files into Houmao storage, or delete temp directories for this ordinary workflow.
- Do not scan existing provider homes to infer the account unless the user explicitly asks for a lower-level recovery workflow.
- Do not promise fully headless Gemini login; the supported flow launches Gemini in an isolated home and the user may need to finish OAuth interactively before exiting Gemini.
- If the command fails and reports a preserved temp home, report that path as recovery context instead of deleting it yourself.
