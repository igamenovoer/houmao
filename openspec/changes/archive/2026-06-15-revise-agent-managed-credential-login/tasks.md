## 1. Login Workflow Guidance

- [x] 1.1 Update `actions/login.md` so Claude, Codex, and Gemini login helpers are started in a dedicated tmux session by default.
- [x] 1.2 Add a concrete proxy-preservation pattern for tmux login sessions covering uppercase and lowercase `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, and `NO_PROXY` variables.
- [x] 1.3 Clarify that the Houmao credential login command still owns provider temp homes, provider CLI invocation, auth artifact import, successful cleanup, and failed-login temp-home reporting.
- [x] 1.4 Clarify that `--inherit-auth-env` is only for intentional provider auth-env preservation and is not required for ordinary proxy inheritance.

## 2. Claude Credential Creation Guidance

- [x] 2.1 Update `actions/add.md` so missing Claude credential input guidance prefers the long-lived Claude Code token path when the user has not chosen a credential kind.
- [x] 2.2 Update `references/claude-credential-kinds.md` to describe `claude setup-token` output as `CLAUDE_CODE_OAUTH_TOKEN` stored through `--oauth-token`.
- [x] 2.3 Distinguish the `ANTHROPIC_AUTH_TOKEN` / `--auth-token` bearer-token lane from the Claude Code setup-token lane.
- [x] 2.4 Keep API key, vendor-login `--config-dir`, optional model/base-url modifiers, and bootstrap-state guidance available without changing their supported flags.

## 3. Validation

- [x] 3.1 Add or update tests or asset assertions that verify the installed credential skill includes tmux login guidance and proxy-variable preservation guidance.
- [x] 3.2 Add or update tests or asset assertions that verify Claude credential-kind guidance prefers `claude setup-token` / `CLAUDE_CODE_OAUTH_TOKEN` for unspecified new Claude credentials.
- [x] 3.3 Run the targeted test suite for system-skill assets, or run `pixi run test` if no narrower suite exists.
- [x] 3.4 Run `openspec status --change "revise-agent-managed-credential-login"` and confirm the change remains apply-ready.
