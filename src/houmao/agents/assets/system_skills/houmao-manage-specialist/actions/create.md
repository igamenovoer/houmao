# Create Specialist

Use this action only when the user wants to create or replace one reusable easy specialist through Houmao's supported higher-level authoring command.

## Workflow

1. Collect the user's intended specialist-create inputs from the current prompt first.
2. If some necessary inputs are missing, look in recent chat context for exact previously stated values.
3. If the specialist name or tool lane is still missing, ask the user in Markdown before proceeding. Prefer a compact table when the tool lane or several required create inputs need clarification.
4. Resolve the intended credential name. If the user did not provide `--credential`, use the documented CLI default `<specialist-name>-creds`.
5. Resolve the credential source mode:
   - Explicit Auth Mode when the user already provided supported auth values or auth files
   - Env Lookup Mode when the user explicitly tells you to inspect specific env names or explicit env-name patterns
   - Directory Scan Mode when the user explicitly points you at one directory and asks you to scan it for likely credentials
   - Auto Credentials Mode when the user explicitly asks for `auto credentials`
   - No Discovery Mode otherwise
6. Treat those credential-source modes as distinct unless the user explicitly asks to combine them.
7. If the active mode is Env Lookup Mode, Directory Scan Mode, or Auto Credentials Mode, load exactly one selected-tool reference page:
   - Claude: `references/claude-credential-lookup.md`
   - Codex: `references/codex-credential-lookup.md`
   - Gemini: `references/gemini-credential-lookup.md`
8. If the active mode is No Discovery Mode and auth inputs are not present, confirm whether that credential bundle already exists for the selected tool. Use the same resolved `houmao-mgr` launcher for `project agents tools <tool> auth get --name <credential>` or `list` when you need that confirmation.
9. If the credential bundle is not confirmed to exist and required auth inputs are still missing after checking current prompt and recent chat context:
   - do not scan env vars, directories, repo-local tool homes, home-dir tool configs, or redirected tool homes unless one of the supported credential-source modes is explicitly active
   - ask the user in Markdown for the missing auth inputs instead of guessing
   - mention that they can either provide auth explicitly, point you at env names or patterns, point you at a directory, or ask for `auto credentials`
10. Run `project easy specialist create` through the resolved launcher.
11. Report the created specialist, selected tool, resolved credential name, and the generated artifact paths returned by the command.

## Credential Source Modes

### Explicit Auth Mode

Use the user-provided auth values or files directly.

- Do not scan env vars, directories, or tool homes unless the user explicitly asked for an additional discovery mode.
- Use only documented create-command auth inputs for the selected tool.

### Env Lookup Mode

Use this only when the user explicitly tells you to inspect env names or explicit env-name patterns.

- Inspect only the current environment entries that match the user's requested names or patterns.
- Do not widen the search into unrelated env vars, files, directories, or automatic tool-home discovery.
- Use the selected tool's reference page to decide which matched env vars are relevant and importable.

### Directory Scan Mode

Use this only when the user explicitly points you at one directory and asks you to scan it for likely credentials for the selected tool.

- Scan only inside the user-provided directory.
- Use the selected tool's reference page to decide which filenames, config files, or env files in that directory are relevant.
- Treat the user's instruction as affirmative permission to scan that directory; do not add extra security warnings first.

### Auto Credentials Mode

Use this only when the user explicitly asks for `auto credentials`.

- Treat `auto credentials` as an instruction, not as a literal CLI flag and not as a replacement for `--credential`.
- Keep the credential bundle name behavior unchanged:
  - `--credential <name>` when the user provided one
  - otherwise the documented default `<specialist-name>-creds`
- Use the selected tool's reference page to follow that tool's supported automatic search order across repo-local candidate homes, redirected homes, home-dir configs, and relevant env vars.

### No Discovery Mode

If the user did not request one of the supported discovery modes:

- do not scan likely current credentials in the system
- only reuse an already-existing credential bundle when you confirmed it exists for the selected tool
- otherwise ask the user for missing auth instead of guessing

## Required Inputs

- `--name`
- `--tool`
- enough auth input for the selected tool unless the intended credential bundle already exists, or one of the active credential-source modes finds one importable credential source for that tool

`--system-prompt` and `--system-prompt-file` are both optional. Use at most one of them.

## Command Shape

Use the resolved launcher with:

```text
<resolved houmao-mgr launcher> project easy specialist create --name <name> --tool <tool> ...
```

Use these documented defaults and options exactly:

- `--credential` defaults to `<name>-creds` when omitted
- `auto credentials` is a user instruction for auth discovery, not a literal `houmao-mgr` flag
- `--setup` defaults to `default` when omitted
- `--no-unattended` is the explicit opt-out from the easy unattended default
- repeatable `--with-skill <dir>` imports selected skill directories
- repeatable `--env-set NAME=value` persists non-credential launch env

Tool-specific auth inputs:

- Claude credential lanes: `--api-key`, optional `--claude-auth-token`, optional `--claude-oauth-token`, optional `--claude-config-dir`, optional `--base-url`, optional `--claude-model`
- Claude optional bootstrap state: `--claude-state-template-file` only for reusable Claude runtime bootstrap state and not a credential-providing method
- Codex: `--api-key`, optional `--base-url`, optional `--codex-org-id`, optional `--codex-auth-json`
- Gemini: `--api-key`, optional `--base-url`, optional `--google-api-key`, optional `--use-vertex-ai`, optional `--gemini-oauth-creds`

Claude vendor-login file usage:

- When the user wants to reuse Claude vendor login files, normalize that request to the directory-based lane `--claude-config-dir <claude-config-root>`.
- If the user points directly at `.credentials.json`, resolve its parent directory and use that directory as `--claude-config-dir`.
- If the user points at both `.credentials.json` and companion `.claude.json`, still use only `--claude-config-dir <root>` rather than inventing separate file flags.
- Treat companion `.claude.json` as part of the same maintained vendor login lane when present, not as a standalone credential input.

## Guardrails

- Do not guess the specialist name, tool lane, or auth values.
- Do not continue specialist creation from partially inferred required inputs when the prompt and recent chat context do not state them explicitly.
- Do not invent API keys, org ids, auth file paths, OAuth credential files, or base URLs.
- Do not scan env vars, directories, repo-local tool homes, `~/.claude`, `~/.codex`, `~/.gemini`, redirected tool homes, or other likely credential locations unless one of the supported credential-source modes is explicitly active.
- Do not widen Env Lookup Mode beyond the user-named env vars or explicit env-name patterns.
- Do not widen Directory Scan Mode beyond the user-provided directory.
- Do not treat `auto credentials` as a literal CLI flag or as the credential bundle name.
- Do not execute `apiKeyHelper`, browser login flows, `codex login`, `claude auth login`, `gemini` interactive login, or other auth-generation flows just to synthesize credentials for specialist creation.
- Do not treat a discovered current auth shape as importable unless it can be faithfully mapped into the selected tool's supported create-command flags.
- Do not invent separate Claude create-command flags for `.credentials.json` or `.claude.json`; the maintained vendor-login lane is `--claude-config-dir`.
- Do not treat a standalone `.claude.json` without the maintained `.credentials.json` config-root login state as a valid Claude credential lane.
- Do not rewrite, minimize, or reinterpret vendor `.credentials.json` content when the task is specialist creation; treat it as opaque vendor login state and map only its containing config root.
- Do not treat only `--claude-state-template-file` or a reusable `claude_state.template.json` as satisfying missing Claude credentials; that file is optional bootstrap state, not a credential lane.
- Do not blindly reuse runtime `.claude.json` as `--claude-state-template-file`; only use an existing reusable `claude_state.template.json` or another explicitly reusable template path.
- Do not mix `--system-prompt` and `--system-prompt-file`.
- Do not treat missing auth as optional unless the intended credential bundle is confirmed to already exist.
