## Context

Houmao already supports importing credential material through `houmao-mgr credentials <tool> add|set` and the project-scoped `houmao-mgr project credentials <tool> add|set` wrapper. The missing operator workflow is the step before import: obtaining a fresh provider auth artifact for a different Codex, Claude, or Gemini account without disturbing the operator's existing provider CLI state.

Each maintained provider has a different local-home contract and login surface:

- Codex can be isolated with `CODEX_HOME`; `codex login --device-auth` writes `auth.json`.
- Claude Code can be isolated with `CLAUDE_CONFIG_DIR`; `claude auth login` writes `.credentials.json` and may also maintain `.claude.json` state.
- Gemini CLI can be isolated with `GEMINI_CLI_HOME`; OAuth login writes `.gemini/oauth_creds.json`, but the available CLI surface is interactive rather than a stable `gemini auth login` subcommand.

The helper should therefore orchestrate the provider CLI in a temporary home, import only through the existing Houmao credential storage contract, and remove temporary secret material after a successful import.

## Goals / Non-Goals

**Goals:**

- Add a credential-login helper under the same top-level and project-scoped command families operators already use for credential management.
- Keep the provider login process authentic: run the installed provider CLI with inherited stdio so browser, device-code, console, and paste-back flows work normally.
- Isolate the login from the operator's current provider account by setting provider home environment variables to a newly created temporary directory.
- Import the resulting auth artifact through existing `add` semantics by default and existing `set` semantics when the operator explicitly requests an update.
- Delete the temporary provider home after a successful import unless the operator explicitly keeps it.
- Preserve the temporary provider home on failure so the operator can inspect vendor errors or retry importing the artifact manually.
- Update the CLI reference and `houmao-credential-mgr` skill so the workflow is discoverable and agent-guided.

**Non-Goals:**

- Reimplementing vendor OAuth/device-auth protocols inside Houmao.
- Guaranteeing login support for every historical or future vendor CLI version; Houmao should provide clear errors when the expected CLI or auth artifact is unavailable.
- Changing the stored credential schema or the existing `add|set|get|list|rename|remove` behavior.
- Automatically merging multiple provider accounts into one credential or inferring account identity from provider metadata.
- Making Gemini OAuth completely non-interactive before the upstream CLI exposes a stable headless login command.

## Decisions

1. The CLI shape will be `houmao-mgr credentials [--project|--agent-def-dir <path>] <tool> login --name <credential-name>` and `houmao-mgr project credentials <tool> login --name <credential-name>`. This keeps login beside the existing credential verbs and reuses the existing target-resolution model.
2. `login` will create a new credential by default and fail if the target name already exists. Operators who intentionally want to replace an existing credential will pass an explicit update flag, such as `--update`, which maps to the existing patch-oriented `set` path after the provider artifact has been captured.
3. The helper will allocate a secure temporary root for the selected provider, set the provider's home env var to that root, and run the provider login command with inherited stdin/stdout/stderr. It will not capture secrets from the terminal transcript.
4. The provider mappings will be explicit:
   - Codex: set `CODEX_HOME=<temp-home>`, run `codex login --device-auth` by default, and import `<temp-home>/auth.json` as `--auth-json`.
   - Claude: set `CLAUDE_CONFIG_DIR=<temp-home>`, run `claude auth login`, and import `<temp-home>/.credentials.json` plus companion `.claude.json` state through the existing `--config-dir` importer.
   - Gemini: set `GEMINI_CLI_HOME=<temp-home>`, launch the interactive `gemini` OAuth flow with temp settings selecting Google login where possible, and import `<temp-home>/.gemini/oauth_creds.json` as `--oauth-creds`.
5. The helper will scrub common ambient provider credential env vars by default so the login command does not silently reuse the current API-key or token lane instead of the isolated temp home. An explicit escape hatch may allow inheriting auth-related env vars for unusual provider setups, but the default must favor account isolation.
6. Cleanup will run only after a successful Houmao import. On success, the temp provider home is deleted by default. On provider login failure, missing expected artifact, or Houmao import failure, the temp home is preserved and its path is reported.
7. The first implementation should share the same import path as the existing `add` and `set` commands rather than creating a new credential writer. This keeps catalog-backed project credentials and direct agent-definition-dir credentials behaviorally aligned.

## Risks / Trade-offs

- Gemini login is less clean than Codex and Claude because the currently observed CLI does not expose a stable headless login command. The design accepts an interactive `gemini` session and requires the operator to finish login and exit before Houmao can import the OAuth file.
- Scrubbing ambient auth env vars can break unusual enterprise setups that rely on those env vars during login. This is intentional by default for multi-account isolation, but the CLI should expose a deliberate override if real workflows require it.
- Preserving temp homes on failure can leave secret material on disk. This is a recovery trade-off: the path is reported, and successful imports remove the temp home automatically.
- Provider CLI behavior changes can break artifact discovery. The implementation should keep provider mappings small, validate expected files explicitly, and return actionable messages rather than attempting broad filesystem searches.
