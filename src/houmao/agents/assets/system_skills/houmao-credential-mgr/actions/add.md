# Add Credential

Use this action only when the user wants to create one new project-local auth bundle.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the tool family, auth display name, and supported auth inputs from the current prompt first and recent chat context second when they were stated explicitly.
3. If the tool family or auth display name is still missing, ask the user in Markdown before proceeding. Prefer a compact table when the tool lane or several required fields are missing.
4. If supported auth inputs are still missing, ask the user for the missing explicit inputs instead of guessing.
5. Run `project agents tools <tool> auth add --name <name> ...`.
6. Report the created auth display name, written env vars, and written auth-file paths returned by the command. If the command returns a projected auth path, treat that path as diagnostic only because the basename is opaque implementation detail.

## Required Inputs

- `tool`: one of `claude`, `codex`, or `gemini`
- `name`
- enough supported auth input for the selected tool

## Command Shape

Use:

```text
<chosen houmao-mgr launcher> project agents tools <tool> auth add --name <name> ...
```

Supported tool-specific inputs:

- Claude: `--api-key`, `--auth-token`, `--oauth-token`, optional `--base-url`, optional `--model`, optional model-selection flags, optional `--state-template-file`, optional `--config-dir`
- Codex: `--api-key`, optional `--base-url`, optional `--org-id`, optional `--auth-json`
- Gemini: `--api-key`, optional `--base-url`, optional `--google-api-key`, optional `--use-vertex-ai`, optional `--oauth-creds`

## Guardrails

- Do not guess the tool family, auth display name, or auth inputs.
- Do not continue with add when required explicit auth inputs are still missing.
- Do not scan env vars, tool homes, or home directories to synthesize auth input unless the user explicitly asked for that narrower inspection.
- Do not invent unsupported file flags for Claude vendor login files; the maintained lane is `--config-dir`.
- Do not treat optional Claude state-template input as a credential-providing method.
- Do not claim that adding one auth bundle also updates any easy profile or explicit launch profile to use it.
- Do not reinterpret `add` as `set` when the auth display name already exists.
