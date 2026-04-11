## ADDED Requirements

### Requirement: Credential login helper imports provider auth artifacts from isolated homes
The dedicated credential interface SHALL expose a `login` verb for each maintained credential lane:

```text
houmao-mgr credentials [--project|--agent-def-dir <path>] <tool> login --name <credential-name>
houmao-mgr project credentials <tool> login --name <credential-name>
```

At minimum, `<tool>` SHALL include `claude`, `codex`, and `gemini`.

The `login` verb SHALL resolve the same project-backed or direct agent-definition-dir target backend as the existing credential verbs before mutating credential storage.

The `login` verb SHALL create a secure temporary provider home, run the installed provider CLI login flow with the selected provider home environment variable pointed at that temporary home, validate that the expected provider auth artifact exists, and import that artifact through the same storage path used by the selected tool lane's existing `add` behavior.

By default, `login` SHALL fail when the selected credential name already exists. When the operator passes an explicit update option, `login` SHALL import the provider artifact through the selected tool lane's existing `set` behavior instead.

The provider-home and artifact mapping SHALL include:

- Codex: `CODEX_HOME=<temp-home>` and `<temp-home>/auth.json`.
- Claude: `CLAUDE_CONFIG_DIR=<temp-home>` and `<temp-home>/.credentials.json`, including companion Claude state such as `.claude.json` when supported by the existing Claude config-dir importer.
- Gemini: `GEMINI_CLI_HOME=<temp-home>` and `<temp-home>/.gemini/oauth_creds.json`.

The provider command mapping SHALL include:

- Codex login defaults to device-auth mode, equivalent to `codex login --device-auth`, while allowing an explicit operator option for the ordinary browser-login mode.
- Claude login runs `claude auth login` and allows supported Claude login-mode flags to pass through when the CLI exposes them.
- Gemini login runs the interactive Gemini OAuth flow in the isolated home and allows the operator to complete the browser or manual-code flow before exiting Gemini so Houmao can import the OAuth artifact.

The `login` verb SHALL scrub common ambient provider credential environment variables by default so the provider login flow does not silently reuse the operator's current API-key or token account instead of the isolated temporary home. If an override exists to inherit auth-related environment variables, it SHALL be explicit.

After a successful Houmao import, the `login` verb SHALL delete the temporary provider home by default. If the provider login fails, the expected auth artifact is missing, or the Houmao import fails, the command SHALL preserve the temporary provider home and report its path. If an explicit keep-temp option is provided, the command SHALL preserve the temporary provider home even after a successful import and report its path.

#### Scenario: Codex device login imports auth json into a new project credential
- **WHEN** an operator runs `houmao-mgr project credentials codex login --name work`
- **AND WHEN** the Codex login flow completes successfully in an isolated `CODEX_HOME`
- **THEN** the command imports the resulting `auth.json` into one new project-local Codex credential named `work`
- **AND THEN** the command deletes the temporary Codex home after the import succeeds

#### Scenario: Existing credential requires explicit update
- **WHEN** one project-local Claude credential named `work` already exists
- **AND WHEN** an operator runs `houmao-mgr project credentials claude login --name work`
- **THEN** the command fails without replacing the existing stored credential
- **AND THEN** the result tells the operator to use the explicit update option when replacement is intended

#### Scenario: Explicit update imports through set behavior
- **WHEN** one direct-dir Gemini credential named `work` already exists under `/tmp/agents`
- **AND WHEN** an operator runs `houmao-mgr credentials gemini login --agent-def-dir /tmp/agents --name work --update`
- **AND WHEN** the Gemini OAuth artifact is produced in the isolated `GEMINI_CLI_HOME`
- **THEN** the command updates the existing Gemini credential through the direct-dir `set` behavior
- **AND THEN** omitted credential fields follow the same preservation semantics as `credentials gemini set`

#### Scenario: Failed provider login preserves the temp home
- **WHEN** an operator runs `houmao-mgr credentials codex login --project --name work`
- **AND WHEN** the Codex login command fails or no `auth.json` is created
- **THEN** the command fails without creating or updating the Houmao credential
- **AND THEN** it preserves the temporary Codex home and reports its path

#### Scenario: Successful import can keep the temp home when requested
- **WHEN** an operator runs `houmao-mgr project credentials claude login --name work --keep-temp-home`
- **AND WHEN** the Claude login flow and Houmao import both succeed
- **THEN** the command creates one project-local Claude credential named `work`
- **AND THEN** it preserves the temporary Claude config home and reports its path

#### Scenario: Login helper avoids ambient provider auth by default
- **WHEN** an operator has provider API-key or token environment variables set in the current shell
- **AND WHEN** the operator runs `houmao-mgr project credentials codex login --name alt-account`
- **THEN** the provider login process runs with the isolated provider home
- **AND THEN** common ambient provider credential environment variables are not inherited unless the operator explicitly asks to inherit them
