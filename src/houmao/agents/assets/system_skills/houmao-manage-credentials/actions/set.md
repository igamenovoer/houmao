# Set Credential

Use this action only when the user wants to update one existing project-local auth bundle.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the tool family, bundle name, and explicit supported changes from the current prompt first and recent chat context second when they were stated explicitly.
3. If the tool family or bundle name is still missing, ask the user in Markdown before proceeding. Prefer a compact table when the tool lane or several required fields are missing.
4. If no supported change is present yet, ask the user for the missing explicit change instead of guessing.
5. If the requested "credential change" is actually a stored easy-profile or explicit launch-profile `--auth` override change, stop and route it as profile authoring instead of running `auth set`.
6. Run `project agents tools <tool> auth set --name <name> ...`.
7. Report the resulting written env vars, cleared env vars, written files, and cleared files returned by the command.

## Required Inputs

- `tool`: one of `claude`, `codex`, or `gemini`
- `name`
- at least one supported change:
  - one or more new explicit auth values or auth files
  - one or more supported clear-style flags for that selected tool

## Command Shape

Use:

```text
<chosen houmao-mgr launcher> project agents tools <tool> auth set --name <name> ...
```

Supported tool-specific changes:

- Claude: explicit env-backed inputs, optional `--state-template-file`, optional `--config-dir`, and the documented `--clear-*` flags exposed by the Claude auth surface
- Codex: explicit env-backed inputs, optional `--auth-json`, and the documented `--clear-api-key`, `--clear-base-url`, `--clear-org-id`, and `--clear-auth-json` flags
- Gemini: explicit env-backed inputs, optional `--oauth-creds`, and the documented `--clear-api-key`, `--clear-base-url`, `--clear-google-api-key`, and `--clear-use-vertex-ai` flags

## Guardrails

- Do not guess the tool family, bundle name, or mutation.
- Do not continue with set when the user has not provided any explicit supported change.
- Do not invent unsupported clear flags or fake symmetric behavior across tools.
- Do not dump raw secret values while explaining the update result.
- Do not use `auth set` when the requested change is only to repoint a reusable easy profile or explicit launch profile at a different auth bundle name.
- Do not route update requests through `add` or direct file editing when `set` is the supported patch-style surface.
