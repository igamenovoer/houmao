# Add Credential

Use this action only when the user wants to create one new credential.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the tool family, credential name, target, and supported credential inputs from the current prompt first and recent chat context second when they were stated explicitly.
3. If the tool family, credential name, target, or required supported inputs are still missing, ask the user before proceeding.
4. Run the selected command.
5. Report the created credential name, written env vars, and written auth-file paths returned by the command.

## Required Inputs

- `tool`: one of `claude`, `codex`, or `gemini`
- `name`
- a resolved target
- enough supported credential input for the selected tool

## Command Shape

Use one of:

```text
<chosen houmao-mgr launcher> project credentials <tool> add --name <name> ...
<chosen houmao-mgr launcher> credentials <tool> add --agent-def-dir <path> --name <name> ...
```

Supported tool-specific inputs:

- Claude: `--api-key`, `--auth-token`, `--oauth-token`, optional `--base-url`, optional `--model`, optional model-selection flags, optional `--state-template-file`, optional `--config-dir`
- Codex: `--api-key`, optional `--base-url`, optional `--org-id`, optional `--auth-json`
- Gemini: `--api-key`, optional `--base-url`, optional `--google-api-key`, optional `--use-vertex-ai`, optional `--oauth-creds`

## Guardrails

- Do not guess the tool family, target, credential name, or credential inputs.
- Do not continue with add when required explicit credential inputs are still missing.
- Do not scan env vars, tool homes, or home directories to synthesize credential input unless the user explicitly asked for that narrower inspection.
- Do not invent unsupported file flags for Claude vendor login files; the maintained lane is `--config-dir`.
- Do not treat optional Claude state-template input as a credential-providing method.
- Do not claim that adding one credential also updates any easy profile or explicit launch profile to use it.
- Do not reinterpret `add` as `set` when the credential already exists.
