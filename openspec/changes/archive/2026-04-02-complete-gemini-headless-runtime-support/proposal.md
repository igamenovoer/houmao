## Why

Houmao already has a Gemini headless backend, but the current lane is not reliable enough to claim full Gemini headless support. Live probing against `gemini-cli` showed three concrete gaps: fresh OAuth-backed Gemini homes fail non-interactive startup unless an auth type is selected, Houmao still resumes Gemini with `--resume latest` instead of the persisted `session_id` that upstream Gemini supports, and Houmao still projects Gemini skills into `.gemini/skills` even though upstream Gemini also supports the generic `.agents/skills` alias and gives it higher precedence within the same scope. In addition, Houmao's current Gemini auth-bundle contract does not expose the API-key plus optional `GOOGLE_GEMINI_BASE_URL` lane that operators need for proxy or compatible-endpoint use.

## What Changes

- Complete Gemini headless startup so freshly constructed Gemini runtime homes can run non-interactively in two supported auth modes:
  - API key mode with optional `GOOGLE_GEMINI_BASE_URL`
  - OAuth mode using `oauth_creds.json`
- Add one explicit Gemini auth-selection strategy for OAuth-backed constructed homes, so Houmao does not depend on a user-global interactive Gemini setup state.
- Extend Houmao's Gemini auth-bundle contract so operators can store API-key, optional endpoint override, and OAuth-backed Gemini inputs through the project-tool workflow.
- Change Gemini managed skill projection to use `.agents/skills` as the primary Gemini skill root for constructed homes and default join-time projection.
- Change Gemini continuation to resume with the persisted Gemini `session_id` instead of `--resume latest`.
- Preserve Gemini’s project-scoped continuation contract by keeping same-working-directory resume enforcement.
- Add tests that exercise Gemini auth preparation for both supported modes, first-turn session capture, and resumed turns by exact session identity.
- Update runtime and operator-facing reference docs so the Gemini headless contract matches actual behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime`: Gemini headless startup, skill projection, and continuation rules need to specify how fresh runtime homes become non-interactive-ready, where Gemini skills are projected, and how resumed turns use the persisted Gemini session identity.
- `houmao-mgr-project-agent-tools`: Gemini auth bundles need to support API-key plus optional endpoint configuration as well as OAuth-backed Gemini credentials through the existing project-tool auth workflow.

## Impact

- Affected code:
  - `src/houmao/agents/realm_controller/backends/gemini_headless.py`
  - `src/houmao/agents/realm_controller/runtime.py`
  - `src/houmao/agents/mailbox_runtime_support.py`
  - `src/houmao/project/assets/starter_agents/tools/gemini/adapter.yaml`
  - `src/houmao/srv_ctrl/commands/project.py`
  - Gemini auth/setup projection and related project-tool support code
- Affected tests:
  - Gemini headless runtime and launch-plan tests
  - Gemini auth projection or project-tool tests
  - Live/manual validation flow for Gemini CLI
- Affected docs:
  - run-phase backend reference
  - Gemini-related project/tool setup guidance
