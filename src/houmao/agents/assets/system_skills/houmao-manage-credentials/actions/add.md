# Add Credential

Use this action only when the user wants to create one new project-local auth bundle.

## Workflow

1. Use the launcher resolved from the top-level skill.
2. Recover the tool family, bundle name, and supported auth inputs from the current prompt first and recent chat context second when they were stated explicitly.
3. If the tool family or bundle name is still missing, ask the user in Markdown before proceeding. Prefer a compact table when the tool lane or several required fields are missing.
4. If supported auth inputs are still missing, ask the user for the missing explicit inputs instead of guessing.
5. Run `project agents tools <tool> auth add --name <name> ...`.
6. Report the created auth bundle, written env vars, and written auth-file paths returned by the command.

## Required Inputs

- `tool`: one of `claude`, `codex`, or `gemini`
- `name`
- enough supported auth input for the selected tool

## Command Shape

Use:

```text
<resolved houmao-mgr launcher> project agents tools <tool> auth add --name <name> ...
```

Supported tool-specific inputs:

- Claude: `--api-key`, `--auth-token`, `--oauth-token`, optional `--base-url`, optional `--model`, optional model-selection flags, optional `--state-template-file`, optional `--config-dir`
- Codex: `--api-key`, optional `--base-url`, optional `--org-id`, optional `--auth-json`
- Gemini: `--api-key`, optional `--base-url`, optional `--google-api-key`, optional `--use-vertex-ai`, optional `--oauth-creds`

## Guardrails

- Do not guess the tool family, bundle name, or auth inputs.
- Do not continue with add when required explicit auth inputs are still missing.
- Do not scan env vars, tool homes, or home directories to synthesize auth input unless the user explicitly asked for that narrower inspection.
- Do not invent unsupported file flags for Claude vendor login files; the maintained lane is `--config-dir`.
- Do not treat optional Claude state-template input as a credential-providing method.
- Do not reinterpret `add` as `set` when the bundle already exists.
