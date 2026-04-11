## Why

Operators who use multiple Claude, Codex, or Gemini accounts currently have to run each vendor CLI login flow by hand, locate the resulting auth files, and then import those files through Houmao's existing credential commands. That is error-prone because each tool uses a different home directory, login command, and import artifact, and it can leave duplicate secret files behind in temporary locations.

## What Changes

- Add a `login` verb under the supported credential-management surface for each maintained tool lane: `houmao-mgr credentials <tool> login ...` and `houmao-mgr project credentials <tool> login ...`.
- Have the login helper create an isolated temporary provider home, run the provider's login flow with the appropriate home environment variable, validate the expected auth artifact, and import it through the existing credential storage contract.
- Support Codex login through `CODEX_HOME` and `auth.json`, Claude login through `CLAUDE_CONFIG_DIR` and `.credentials.json` plus companion `.claude.json`, and Gemini OAuth login through `GEMINI_CLI_HOME` and `.gemini/oauth_creds.json`.
- Delete the temporary provider home after a successful import by default, while preserving it on failure for diagnosis and retry.
- Document the new operator workflow and update the packaged `houmao-credential-mgr` skill so agents can route credential-login requests through the supported command instead of inventing ad hoc filesystem steps.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-mgr-credentials-cli`: add the credential `login` verb and its provider-specific orchestration contract.
- `docs-cli-reference`: document the new credential-login workflow, options, provider mappings, and temp-home cleanup semantics.
- `houmao-manage-credentials-skill`: update the packaged `houmao-credential-mgr` skill contract so it can route and explain the new login action.

## Impact

- Affected CLI code: `src/houmao/srv_ctrl/commands/credentials.py`.
- Affected tests: `tests/unit/srv_ctrl/test_credentials_commands.py` and any project-credential command tests that assert help or supported verbs.
- Affected docs and skills: `docs/reference/cli/houmao-mgr.md` and `src/houmao/agents/assets/system_skills/houmao-credential-mgr/`.
- External tool behavior: invokes installed `codex`, `claude`, or `gemini` executables and lets their interactive/browser/device-login UX pass through to the operator.
