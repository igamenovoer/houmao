# Login Credential

Use this action only when the user wants to run a provider login flow for a fresh Claude, Codex, or Gemini account and import the resulting auth file into Houmao credential storage.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the tool family, credential name, target, and whether this is a create or explicit update from the current prompt first and recent chat context second when they were stated explicitly.
3. If the tool family, credential name, or target is still missing, ask the user before proceeding.
4. Use the default create-only login behavior unless the user explicitly said to update, replace, or refresh an existing credential.
5. Run the selected command and let the user complete any provider browser, device-code, console, or paste-back authentication steps.
6. Report the credential name, provider command, and temp-home cleanup status returned by the command.

## Required Inputs

- `tool`: one of `claude`, `codex`, or `gemini`
- `name`
- a resolved target

## Command Shape

Use one of:

```text
<chosen houmao-mgr launcher> project credentials <tool> login --name <name>
<chosen houmao-mgr launcher> credentials <tool> login --agent-def-dir <path> --name <name>
```

Use `--update` only when the user explicitly intends to replace an existing credential:

```text
<chosen houmao-mgr launcher> project credentials <tool> login --name <name> --update
<chosen houmao-mgr launcher> credentials <tool> login --agent-def-dir <path> --name <name> --update
```

Common options:

- `--keep-temp-home`: preserve the temporary provider home after a successful import.
- `--inherit-auth-env`: allow ambient provider auth-related environment variables to reach the provider login process.

Provider-specific options:

- Claude: `--claudeai`, `--console`, `--email <value>`, `--sso`
- Codex: `--browser` to use ordinary browser login instead of the default device-auth login
- Gemini: `--no-browser` to set `NO_BROWSER=true` for the OAuth flow

## Guardrails

- Do not guess the tool family, target, or credential name.
- Do not add `--update` unless the user explicitly asked to update, replace, or refresh an existing credential.
- Do not manually create provider home directories, run provider login commands, copy auth files into Houmao storage, or delete temp directories for this ordinary workflow.
- Do not scan existing provider homes to infer the account unless the user explicitly asks for a lower-level recovery workflow.
- Do not promise fully headless Gemini login; the supported flow launches Gemini in an isolated home and the user may need to finish OAuth interactively before exiting Gemini.
- If the command fails and reports a preserved temp home, report that path as recovery context instead of deleting it yourself.
