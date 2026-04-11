## 1. CLI Surface

- [x] 1.1 Add `login` to the maintained credential tool lanes for `houmao-mgr credentials [--project|--agent-def-dir <path>] <tool>` and `houmao-mgr project credentials <tool>`.
- [x] 1.2 Add common login options for credential name, explicit update behavior, temp-home retention, and explicit auth-env inheritance.
- [x] 1.3 Add provider-specific login options for Codex device/browser mode, Claude auth-login mode flags, and Gemini manual-browser behavior as supported by the design.

## 2. Login Orchestration

- [x] 2.1 Implement a shared temporary provider-home helper that creates a secure temp directory, records its path, and centralizes success/failure cleanup behavior.
- [x] 2.2 Implement provider environment construction for Codex `CODEX_HOME`, Claude `CLAUDE_CONFIG_DIR`, and Gemini `GEMINI_CLI_HOME`.
- [x] 2.3 Scrub common ambient provider credential env vars by default and honor the explicit inherit-auth-env override.
- [x] 2.4 Run the selected provider login command with inherited stdin/stdout/stderr and clear failure reporting.
- [x] 2.5 Validate expected provider artifacts for Codex `auth.json`, Claude `.credentials.json` plus supported companion state, and Gemini `.gemini/oauth_creds.json`.

## 3. Credential Import

- [x] 3.1 Reuse the existing target-resolution path for project-backed and direct agent-definition-dir credentials before running mutating login behavior.
- [x] 3.2 Import successful Codex login output through the existing Codex `--auth-json` add/set behavior.
- [x] 3.3 Import successful Claude login output through the existing Claude `--config-dir` add/set behavior.
- [x] 3.4 Import successful Gemini login output through the existing Gemini `--oauth-creds` add/set behavior.
- [x] 3.5 Enforce create-only default behavior for duplicate names and route explicit update requests through existing patch-oriented `set` semantics.

## 4. Tests

- [x] 4.1 Add unit tests for login command help and routing under both `credentials` and `project credentials`.
- [x] 4.2 Add fake-provider-command tests covering provider env mapping, ambient auth-env scrubbing, inherited-artifact validation, and provider command failure reporting.
- [x] 4.3 Add tests proving successful imports delete the temporary provider home by default and `--keep-temp-home` preserves it.
- [x] 4.4 Add tests proving failed provider login, missing artifact, and failed Houmao import preserve and report the temporary provider home.
- [x] 4.5 Add backend tests for create-only duplicate rejection and explicit update behavior across project-backed and direct-dir targets where coverage is missing.

## 5. Documentation And Skill

- [x] 5.1 Update `docs/reference/cli/houmao-mgr.md` with the credential login command forms, provider mappings, options, interactive expectations, and cleanup semantics.
- [x] 5.2 Update the packaged `houmao-credential-mgr` skill router to include `login`.
- [x] 5.3 Add or update login-specific skill guidance explaining target selection, duplicate/update behavior, temp-home ownership, and the no-manual-copying rule.

## 6. Verification

- [x] 6.1 Run `pixi run test` or the focused credential command test subset if the full unit suite is not practical.
- [x] 6.2 Run `pixi run lint` and `pixi run typecheck`.
- [x] 6.3 Run `pixi run openspec status --change "add-credential-login-helper"` and confirm the change is ready for implementation.
