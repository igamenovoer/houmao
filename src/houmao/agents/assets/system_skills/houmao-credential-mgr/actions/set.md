# Set Credential

Use this action only when the user wants to update one existing credential.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the tool family, credential name, target, and explicit supported changes from the current prompt first and recent chat context second when they were stated explicitly.
3. If the tool family, credential name, target, or supported change is still missing, ask the user before proceeding.
4. If the requested "credential change" is actually a stored project-profile or launch-dossier `--auth` override change, stop and route it as profile authoring instead of running `set`.
5. Render the selected command template: `project.credentials.<tool>.set` for the project lane or `credentials.<tool>.set` for the plain agent-definition lane.
6. Run the rendered `argv` only if there are no blockers.
7. Report the resulting written env vars, cleared env vars, written files, and cleared files returned by the command.

## Required Inputs

- `tool`: one of `claude`, `codex`, or `gemini`
- `name`
- a resolved target
- at least one supported change:
  - one or more new explicit credential values or auth files
  - one or more supported clear-style flags for that selected tool

## Command Shape

Use the matching CLI-owned template, then run its rendered `argv`:

```text
<chosen houmao-mgr launcher> --print-json internals command-templates render --id project.credentials.<tool>.set --intent '<json>'
<chosen houmao-mgr launcher> --print-json internals command-templates render --id credentials.<tool>.set --intent '<json>'
```

Use `show --id <template-id>` for the authoritative tool-specific update fields, clear flags, and conflicts.

## Guardrails

- Do not guess the tool family, target, credential name, or mutation.
- Do not continue with set when the user has not provided any explicit supported change.
- Do not invent unsupported clear flags or fake symmetric behavior across tools.
- Do not dump raw secret values while explaining the update result.
- Do not use `set` when the requested change is only to repoint a reusable project profile or native launch dossier at a different credential name.
- Do not route update requests through `add` or direct file editing when `set` is the supported patch-style surface.
- Do not duplicate Claude/Codex/Gemini option menus from skill prose; use the template metadata.
