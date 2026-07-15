# Add Credential

Use this action only when the user wants to create one new credential.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the tool family, credential name, target, and supported credential inputs from the current prompt first and recent chat context second when they were stated explicitly.
3. If the tool family, credential name, target, or required supported inputs are still missing, load the kinds reference for the selected tool and present the enumerated kinds as a menu to the user before proceeding:
   - Claude: `references/claude-credential-kinds.md`
   - Codex: `references/codex-credential-kinds.md`
   - Kimi: `references/kimi-credential-kinds.md`
   For Claude, when the user has not already chosen a credential kind, present the long-lived Claude Code token from `claude setup-token` as the preferred default. That token maps to `--oauth-token` / `CLAUDE_CODE_OAUTH_TOKEN`. Keep API key, bearer auth token, OAuth token, and vendor-login config-directory choices available when the user selects one explicitly or cannot use `claude setup-token`.
4. Build the direct command: `project credentials <tool> add` for the project lane or `internals native-agent credentials <tool> add` for the direct native-agent lane.
5. Run the direct command only after required inputs are explicit and conflicts are resolved.
6. Report the created credential name, written env vars, and written auth-file paths returned by the command.

## Required Inputs

- `tool`: one of `claude`, `codex`, or `kimi`
- `name`
- a resolved target
- enough supported credential input for the selected tool

## Command Shape

Run the matching direct command:

```bash
<chosen houmao-mgr launcher> project credentials <tool> add --name <credential> [<tool-specific credential flags>]
<chosen houmao-mgr launcher> internals native-agent credentials <tool> add --native-agent-root <dir> --name <credential> [<tool-specific credential flags>]
```

Use the selected tool's credential-kind reference for supported credential flags.

## Guardrails

- Do not guess the tool family, target, credential name, or credential inputs.
- Do not continue with add when required explicit credential inputs are still missing.
- Do not scan env vars, tool homes, or home directories to synthesize credential input unless the user explicitly asked for that narrower inspection.
- Do not silently choose a Claude credential value. Prefer the `claude setup-token` / `--oauth-token` lane only as guidance when Claude credential material is missing; still obtain the token or another supported credential input explicitly before running `add`.
- Do not invent unsupported file flags for Claude vendor login files; the maintained lane is `--config-dir`.
- Do not treat optional Claude state-template input as a credential-providing method.
- Do not claim that adding one credential also updates any project profile or native launch dossier to use it.
- Do not reinterpret `add` as `set` when the credential already exists.
- Do not duplicate unsupported Claude/Codex/Kimi options; use the selected tool reference before choosing credential flags.
