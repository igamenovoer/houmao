# Set Credential

Use this action only when the user wants to update one existing credential.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the tool family, credential name, target, and explicit supported changes from the current prompt first and recent chat context second when they were stated explicitly.
3. If the tool family, credential name, target, or supported change is still missing, ask the user before proceeding.
4. If the requested "credential change" is actually a stored project-profile or launch-dossier `--auth` override change, stop and route it as profile authoring instead of running `set`.
5. Build the direct command: `project credentials <tool> set` for the project lane or `internals native-agent credentials <tool> set` for the direct native-agent lane.
6. Run the direct command only after required inputs are explicit and conflicts are resolved.
7. Report the resulting written env vars, cleared env vars, written files, and cleared files returned by the command.

## Required Inputs

- `tool`: one of `claude`, `codex`, `kimi`, or `gemini`
- `name`
- a resolved target
- at least one supported change:
  - one or more new explicit credential values or auth files
  - one or more supported clear-style flags for that selected tool

## Command Shape

Run the matching direct command:

```bash
<chosen houmao-mgr launcher> project credentials <tool> set --name <credential> [<tool-specific update or clear flags>]
<chosen houmao-mgr launcher> internals native-agent credentials <tool> set --native-agent-root <dir> --name <credential> [<tool-specific update or clear flags>]
```

Use the selected tool's credential-kind reference for supported update and clear flags.

## Guardrails

- Do not guess the tool family, target, credential name, or mutation.
- Do not continue with set when the user has not provided any explicit supported change.
- Do not invent unsupported clear flags or fake symmetric behavior across tools.
- Do not dump raw secret values while explaining the update result.
- Do not use `set` when the requested change is only to repoint a reusable project profile or native launch dossier at a different credential name.
- Do not route update requests through `add` or direct file editing when `set` is the supported patch-style surface.
- Do not duplicate unsupported Claude/Codex/Gemini/Kimi options; use the selected tool reference before choosing update or clear flags.
