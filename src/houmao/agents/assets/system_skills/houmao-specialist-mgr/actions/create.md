# Create Or Edit Specialist/Easy Profile

Use this action only when the user wants to create or patch one reusable easy specialist, or create, patch, or replace one reusable specialist-backed easy profile through Houmao's supported higher-level authoring commands.

## Workflow

1. Determine whether the target resource is `specialist` or `profile`.
2. For specialist work, determine whether the user wants a new specialist, a patch edit to an existing specialist, or same-name replacement.
3. For profile work, determine whether the user wants a new profile, a patch edit to an existing profile, or same-name replacement.
4. If the target resource kind or authoring operation is still ambiguous after checking the prompt and recent chat context, ask the user before proceeding.
5. Use the `houmao-mgr` launcher already chosen by the top-level skill.
6. If the target resource is `profile`, follow `Profile Authoring Workflow` below and stop after reporting the result.
7. For specialist patch edits, follow `Specialist Set Workflow` below and stop after reporting the result.
8. Otherwise follow `Specialist Create Workflow` below.

## Profile Authoring Workflow

1. Collect the user's intended easy-profile inputs from the current prompt first.
2. If some necessary inputs are missing, look in recent chat context for exact previously stated values.
3. Treat wording such as `edit`, `update`, `patch`, `change defaults`, or `set defaults` as a request for `project easy profile set`.
4. Treat wording such as `replace`, `recreate`, or `overwrite` as a request for `project easy profile create --yes`; replacement is same-lane only and clears omitted optional defaults.
5. For patch edits, require the profile name and at least one update or clear flag. If no update is stated, ask before proceeding.
6. For profile creation or replacement, require the profile name and source specialist. If either is still missing, ask the user in Markdown before proceeding. Prefer a short bullet list when you only need one or two fields.
7. Run `project easy profile set` for patch edits, or `project easy profile create` with `--yes` only for intended same-name replacement.
8. Report the profile name, source specialist when returned, and returned defaults metadata.

## Specialist Create Workflow

1. Collect the user's intended specialist-create inputs from the current prompt first.
2. If some necessary inputs are missing, look in recent chat context for exact previously stated values.
3. If the specialist name or tool lane is still missing, ask the user in Markdown before proceeding. Prefer a compact table when the tool lane or several required create inputs need clarification.
4. Resolve the intended credential display name. If the user did not provide `--credential`, use the documented CLI default `<specialist-name>-creds`.
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
8. If the active mode is No Discovery Mode and auth inputs are not present, confirm whether that credential bundle already exists for the selected tool. Use the same chosen `houmao-mgr` launcher for `project credentials <tool> get --name <credential>` or `list` when you need that confirmation.
9. If the credential bundle is not confirmed to exist and required auth inputs are still missing after checking current prompt and recent chat context:
   - do not scan env vars, directories, repo-local tool homes, home-dir tool configs, or redirected tool homes unless one of the supported credential-source modes is explicitly active
   - load the kinds reference for the selected tool and present the enumerated kinds as a menu to the user:
     - Claude: `references/claude-credential-kinds.md`
     - Codex: `references/codex-credential-kinds.md`
     - Gemini: `references/gemini-credential-kinds.md`
   - ask the user in Markdown for the missing auth inputs instead of guessing
   - mention that they can either provide auth explicitly, point you at env names or patterns, point you at a directory, or ask for `auto credentials`
10. Run `project easy specialist create` through the chosen `houmao-mgr` launcher.
11. Report the created specialist, selected tool, resolved credential display name, and the generated artifact paths returned by the command.

## Specialist Set Workflow

1. Collect the user's intended specialist patch inputs from the current prompt first.
2. If some necessary inputs are missing, look in recent chat context for exact previously stated values.
3. Require the specialist name and at least one update or clear flag. If no update is stated, ask before proceeding.
4. Treat prompt, skill, setup, credential, prompt-mode, model, reasoning-level, and env changes as `project easy specialist set` work.
5. If the user asks to rename the specialist or change its tool lane, explain that `project easy specialist set` intentionally does not support that identity change and ask whether to create a new specialist instead.
6. For credential changes, require an existing credential display name for the specialist's current tool lane. Use `project easy specialist get --name <name>` if you need to inspect the current tool before confirming or applying the credential change.
7. For `--add-skill <name>`, require the project skill name. For `--with-skill <dir>`, require a skill directory path that contains `SKILL.md`.
8. For env changes, treat repeatable `--env-set NAME=value` as replacing the specialist's stored env mapping. Use `--clear-env` only when the user explicitly wants the mapping removed.
9. Run `project easy specialist set` through the chosen `houmao-mgr` launcher.
10. Report the updated specialist, selected tool, resolved credential display name, skills, and launch metadata returned by the command.

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
- Keep the credential display-name behavior unchanged:
  - `--credential <name>` when the user provided one
  - otherwise the documented default `<specialist-name>-creds`
- Treat the credential name as a user-facing auth display name only; project-local storage paths use opaque refs and are not a supported input surface.
- Use the selected tool's reference page to follow that tool's supported automatic search order across repo-local candidate homes, redirected homes, home-dir configs, and relevant env vars.

### No Discovery Mode

If the user did not request one of the supported discovery modes:

- do not scan likely current credentials in the system
- only reuse an already-existing credential bundle when you confirmed it exists for the selected tool
- otherwise ask the user for missing auth instead of guessing

## Profile Command Shapes

Use the chosen `houmao-mgr` launcher with one of:

```text
<chosen houmao-mgr launcher> project easy profile create --name <profile> --specialist <specialist> ...
<chosen houmao-mgr launcher> project easy profile create --name <profile> --specialist <specialist> --yes ...
<chosen houmao-mgr launcher> project easy profile set --name <profile> ...
```

Required inputs for create and replacement:

- `--name`
- `--specialist`

Required inputs for patch edits:

- `--name`
- at least one update or clear option

Common optional inputs:

- `--agent-name`
- `--agent-id`
- `--workdir`
- `--auth`
- `--model`
- `--reasoning-level`
- `--prompt-mode unattended|as_is`
- repeatable `--env-set NAME=value`
- `--mail-transport filesystem|stalwart`
- `--mail-principal-id`
- `--mail-address`
- `--mail-root`
- `--mail-base-url`
- `--mail-jmap-url`
- `--mail-management-url`
- `--headless`
- `--no-gateway`
- `--managed-header` / `--no-managed-header`
- repeatable `--managed-header-section SECTION=enabled|disabled`
- `--gateway-port`
- `--prompt-overlay-mode append|replace`
- `--prompt-overlay-text`
- `--prompt-overlay-file`
- `--memo-seed-text`
- `--memo-seed-file`
- `--memo-seed-dir`
- `--memo-seed-policy initialize|replace|fail-if-nonempty`

Common clear inputs for `profile set`:

- `--clear-agent-name`
- `--clear-agent-id`
- `--clear-workdir`
- `--clear-auth`
- `--clear-model`
- `--clear-reasoning-level`
- `--clear-prompt-mode`
- `--clear-env`
- `--clear-mailbox`
- `--clear-headless`
- `--clear-managed-header`
- `--clear-managed-header-section SECTION`
- `--clear-managed-header-sections`
- `--clear-prompt-overlay`
- `--clear-memo-seed`

Profile authoring rules:

- use `project easy profile set` for ordinary edits; do not remove and recreate a profile just to patch defaults
- use `project easy profile create --yes` only when the user intends same-name replacement; replacement clears omitted optional fields and cannot replace an explicit `project agents launch-profiles` entry with the same name
- use `project agents launch-profiles set` only for explicit recipe-backed launch profiles, not easy profiles
- do not mix `--prompt-overlay-text` and `--prompt-overlay-file`
- prompt-overlay text requires `--prompt-overlay-mode append|replace`
- do not mix `--memo-seed-text`, `--memo-seed-file`, and `--memo-seed-dir`; use at most one source
- `--memo-seed-policy` on `profile set` requires one new memo-seed source or an existing stored memo seed
- `--clear-memo-seed` cannot be combined with one new memo-seed source or `--memo-seed-policy`
- `--mail-transport` is required when any declarative mailbox fields are present
- `filesystem` mailbox defaults accept `--mail-root` and reject the Stalwart URL flags
- `stalwart` mailbox defaults accept the Stalwart URL flags and reject `--mail-root`
- `--no-gateway` and `--gateway-port` cannot be combined
- `--managed-header-section` stores sparse per-section policy for the supported sections `identity`, `memo-cue`, `houmao-runtime-guidance`, `automation-notice`, `task-reminder`, and `mail-ack`
- `--clear-managed-header-section` removes one stored section policy entry, and `--clear-managed-header-sections` removes all stored section policy entries
- `--auth` is only the stored auth display-name override for later launches; it does not create credentials, and the stored relationship continues to resolve after auth rename

## Specialist Create Required Inputs

- `--name`
- `--tool`
- enough auth input for the selected tool unless the intended credential bundle already exists, or one of the active credential-source modes finds one importable credential source for that tool

`--system-prompt` and `--system-prompt-file` are both optional. Use at most one of them.

## Specialist Create Command Shape

Use the chosen `houmao-mgr` launcher with:

```text
<chosen houmao-mgr launcher> project easy specialist create --name <name> --tool <tool> ...
```

Use these documented defaults and options exactly:

- `--credential` defaults to `<name>-creds` when omitted and supplies the auth display name
- `auto credentials` is a user instruction for auth discovery, not a literal `houmao-mgr` flag
- `--setup` defaults to `default` when omitted
- `--no-unattended` is the explicit opt-out from the easy unattended default
- repeatable `--with-skill <dir>` imports selected skill directories
- repeatable `--env-set NAME=value` persists non-credential launch env

## Specialist Set Command Shape

Use the chosen `houmao-mgr` launcher with:

```text
<chosen houmao-mgr launcher> project easy specialist set --name <name> ...
```

Required inputs for patch edits:

- `--name`
- at least one update or clear option

Common update and clear inputs:

- `--system-prompt`
- `--system-prompt-file`
- `--clear-system-prompt`
- `--with-skill <dir>`
- `--add-skill <name>`
- `--remove-skill <name>`
- `--clear-skills`
- `--setup <name>`
- `--credential <name>`
- `--prompt-mode unattended|as_is`
- `--clear-prompt-mode`
- `--model`
- `--clear-model`
- `--reasoning-level`
- `--clear-reasoning-level`
- repeatable `--env-set NAME=value`
- `--clear-env`

Specialist patch rules:

- use `project easy specialist set` for ordinary edits; do not remove and recreate a specialist just to change prompt, skills, setup, credential, prompt-mode, model, reasoning-level, or env
- do not pass `--tool`; set preserves the existing specialist tool lane
- do not try to rename the specialist through set; create a new specialist when the name should change
- `--env-set` replaces the specialist's stored env mapping with the repeated records supplied on that command
- `--with-skill <dir>` imports and adds a skill directory; `--add-skill <name>` adds an already projected project skill by name
- `--credential <name>` selects an existing credential display name for the specialist's current tool lane; it does not create credentials
- set updates future launches and profile resolutions, not already-running easy instances

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

- Do not guess whether the user wants to create a reusable specialist or a reusable easy profile.
- Do not guess whether easy-profile work is a patch edit or same-name replacement.
- Do not guess the profile name, source specialist, or update fields for easy-profile authoring.
- Do not enter credential discovery or credential import workflow for easy-profile creation.
- Do not treat profile creation as launching or mutating a live easy instance.
- Do not remove and recreate an easy profile for ordinary default edits; use `project easy profile set`.
- Do not remove and recreate an easy specialist for ordinary prompt, skill, setup, credential, prompt-mode, model, reasoning-level, or env edits; use `project easy specialist set`.
- Do not use `project agents launch-profiles set` for easy-profile edits.
- Do not use `project easy specialist set` for specialist rename or tool-lane changes.
- Do not mix `--prompt-overlay-text` and `--prompt-overlay-file` for easy-profile creation.
- Do not guess the specialist name, tool lane, or auth values.
- Do not continue specialist creation from partially inferred required inputs when the prompt and recent chat context do not state them explicitly.
- Do not invent API keys, org ids, auth file paths, OAuth credential files, or base URLs.
- Do not scan env vars, directories, repo-local tool homes, `~/.claude`, `~/.codex`, `~/.gemini`, redirected tool homes, or other likely credential locations unless one of the supported credential-source modes is explicitly active.
- Do not widen Env Lookup Mode beyond the user-named env vars or explicit env-name patterns.
- Do not widen Directory Scan Mode beyond the user-provided directory.
- Do not treat `auto credentials` as a literal CLI flag or as the auth display name.
- Do not execute `apiKeyHelper`, browser login flows, `codex login`, `claude auth login`, `gemini` interactive login, or other auth-generation flows just to synthesize credentials for specialist creation.
- Do not treat a discovered current auth shape as importable unless it can be faithfully mapped into the selected tool's supported create-command flags.
- Do not invent separate Claude create-command flags for `.credentials.json` or `.claude.json`; the maintained vendor-login lane is `--claude-config-dir`.
- Do not treat a standalone `.claude.json` without the maintained `.credentials.json` config-root login state as a valid Claude credential lane.
- Do not rewrite, minimize, or reinterpret vendor `.credentials.json` content when the task is specialist creation; treat it as opaque vendor login state and map only its containing config root.
- Do not treat only `--claude-state-template-file` or a reusable `claude_state.template.json` as satisfying missing Claude credentials; that file is optional bootstrap state, not a credential lane.
- Do not blindly reuse runtime `.claude.json` as `--claude-state-template-file`; only use an existing reusable `claude_state.template.json` or another explicitly reusable template path.
- Do not mix `--system-prompt` and `--system-prompt-file`.
- Do not treat missing auth as optional unless the intended credential bundle is confirmed to already exist.
- Do not infer auth identity from `.houmao/content/auth/...` or `.houmao/agents/tools/<tool>/auth/...` directory basenames.
