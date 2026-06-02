# Add Credential

Use this action only when the user wants to create one new credential.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the tool family, credential name, target, and supported credential inputs from the current prompt first and recent chat context second when they were stated explicitly.
3. If the tool family, credential name, target, or required supported inputs are still missing, load the kinds reference for the selected tool and present the enumerated kinds as a menu to the user before proceeding:
   - Claude: `references/claude-credential-kinds.md`
   - Codex: `references/codex-credential-kinds.md`
   - Gemini: `references/gemini-credential-kinds.md`
4. Render the selected command template: `project.credentials.<tool>.add` for the project lane or `credentials.<tool>.add` for the plain agent-definition lane.
5. Run the rendered `argv` only if there are no blockers.
6. Report the created credential name, written env vars, and written auth-file paths returned by the command.

## Required Inputs

- `tool`: one of `claude`, `codex`, or `gemini`
- `name`
- a resolved target
- enough supported credential input for the selected tool

## Command Shape

Use the matching CLI-owned template, then run its rendered `argv`:

```text
<chosen houmao-mgr launcher> --print-json internals command-templates render --id project.credentials.<tool>.add --intent '<json>'
<chosen houmao-mgr launcher> --print-json internals command-templates render --id credentials.<tool>.add --intent '<json>'
```

Use `show --id <template-id>` for the authoritative tool-specific fields, clear rules, and conflicts.

## Guardrails

- Do not guess the tool family, target, credential name, or credential inputs.
- Do not continue with add when required explicit credential inputs are still missing.
- Do not scan env vars, tool homes, or home directories to synthesize credential input unless the user explicitly asked for that narrower inspection.
- Do not invent unsupported file flags for Claude vendor login files; the maintained lane is `--config-dir`.
- Do not treat optional Claude state-template input as a credential-providing method.
- Do not claim that adding one credential also updates any project profile or native launch dossier to use it.
- Do not reinterpret `add` as `set` when the credential already exists.
- Do not duplicate Claude/Codex/Gemini option menus from skill prose; use the template metadata.
