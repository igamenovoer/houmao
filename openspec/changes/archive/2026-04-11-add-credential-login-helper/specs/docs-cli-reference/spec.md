## ADDED Requirements

### Requirement: CLI reference documents the credential login helper
The CLI reference SHALL document the credential `login` helper for the dedicated credential-management families.

At minimum, that coverage SHALL include:

- the top-level form `houmao-mgr credentials [--project|--agent-def-dir <path>] <tool> login --name <credential-name>`,
- the project-scoped wrapper form `houmao-mgr project credentials <tool> login --name <credential-name>`,
- the supported tool lanes `claude`, `codex`, and `gemini`,
- the default create-only behavior and the explicit update option for replacing an existing credential,
- provider home isolation through `CODEX_HOME`, `CLAUDE_CONFIG_DIR`, and `GEMINI_CLI_HOME`,
- provider artifact imports from Codex `auth.json`, Claude `.credentials.json` plus supported companion state, and Gemini `.gemini/oauth_creds.json`,
- successful cleanup of the temporary provider home by default,
- preservation of the temporary provider home on failure or when an explicit keep-temp option is used,
- provider-specific login expectations, including Codex device-auth default, Claude `auth login`, and Gemini's interactive OAuth flow.

The CLI reference SHALL explain that the helper invokes installed provider CLIs and that the operator may need to complete browser, device-code, console, or paste-back authentication steps before Houmao imports the resulting file.

#### Scenario: Reader can find the top-level credential login form
- **WHEN** a reader looks up `houmao-mgr credentials`
- **THEN** the CLI reference lists `login` as a supported credential action for `claude`, `codex`, and `gemini`
- **AND THEN** it explains how to select a project target or a direct agent-definition-dir target

#### Scenario: Reader understands successful cleanup and failure preservation
- **WHEN** a reader looks up the credential login workflow
- **THEN** the CLI reference states that the temporary provider home is deleted after a successful import by default
- **AND THEN** it states that the temporary provider home is preserved and reported when provider login, artifact validation, or Houmao import fails

#### Scenario: Reader sees provider-specific login behavior
- **WHEN** a reader compares Codex, Claude, and Gemini credential login behavior
- **THEN** the CLI reference identifies the provider home env var and expected auth artifact for each tool
- **AND THEN** it explains that Gemini may require an interactive OAuth session rather than a fully headless login command
