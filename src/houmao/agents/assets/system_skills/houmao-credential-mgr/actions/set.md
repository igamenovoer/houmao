# Set Credential

Use this action only when the user wants to update one existing credential.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the tool family, credential name, target, and explicit supported changes from the current prompt first and recent chat context second when they were stated explicitly.
3. If the tool family, credential name, target, or supported change is still missing, ask the user before proceeding.
4. If the requested "credential change" is actually a stored easy-profile or explicit launch-profile `--auth` override change, stop and route it as profile authoring instead of running `set`.
5. Run the selected command.
6. Report the resulting written env vars, cleared env vars, written files, and cleared files returned by the command.

## Required Inputs

- `tool`: one of `claude`, `codex`, or `gemini`
- `name`
- a resolved target
- at least one supported change:
  - one or more new explicit credential values or auth files
  - one or more supported clear-style flags for that selected tool

## Command Shape

Use one of:

```text
<chosen houmao-mgr launcher> project credentials <tool> set --name <name> ...
<chosen houmao-mgr launcher> credentials <tool> set --agent-def-dir <path> --name <name> ...
```

Supported tool-specific changes:

- Claude: explicit env-backed inputs, optional `--state-template-file`, optional `--config-dir`, and the documented `--clear-*` flags exposed by the Claude credential surface
- Codex: explicit env-backed inputs, optional `--auth-json`, and the documented `--clear-api-key`, `--clear-base-url`, `--clear-org-id`, and `--clear-auth-json` flags
- Gemini: explicit env-backed inputs, optional `--oauth-creds`, and the documented `--clear-api-key`, `--clear-base-url`, `--clear-google-api-key`, and `--clear-use-vertex-ai` flags

## Guardrails

- Do not guess the tool family, target, credential name, or mutation.
- Do not continue with set when the user has not provided any explicit supported change.
- Do not invent unsupported clear flags or fake symmetric behavior across tools.
- Do not dump raw secret values while explaining the update result.
- Do not use `set` when the requested change is only to repoint a reusable easy profile or explicit launch profile at a different credential name.
- Do not route update requests through `add` or direct file editing when `set` is the supported patch-style surface.
