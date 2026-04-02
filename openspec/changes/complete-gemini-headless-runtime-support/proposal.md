## Why

Houmao already has a Gemini headless backend, but the current lane is not reliable enough to claim full Gemini headless support. Live probing against `gemini-cli` showed two concrete gaps: fresh OAuth-backed Gemini homes fail non-interactive startup unless an auth type is selected, and Houmao still resumes Gemini with `--resume latest` instead of the persisted `session_id` that upstream Gemini supports.

## What Changes

- Complete Gemini headless startup so a freshly constructed Gemini runtime home can run non-interactively with OAuth-backed credentials.
- Add one explicit Gemini auth-selection strategy for constructed homes, so Houmao does not depend on a user-global interactive setup state.
- Change Gemini continuation to resume with the persisted Gemini `session_id` instead of `--resume latest`.
- Preserve Gemini’s project-scoped continuation contract by keeping same-working-directory resume enforcement.
- Add tests that exercise Gemini headless auth preparation, first-turn session capture, and resumed turns by exact session identity.
- Update runtime and operator-facing reference docs so the Gemini headless contract matches actual behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime`: Gemini headless startup and continuation rules need to specify how fresh runtime homes become non-interactive-ready and how resumed turns use the persisted Gemini session identity.

## Impact

- Affected code:
  - `src/houmao/agents/realm_controller/backends/gemini_headless.py`
  - `src/houmao/agents/realm_controller/runtime.py`
  - `src/houmao/project/assets/starter_agents/tools/gemini/adapter.yaml`
  - Gemini auth/setup projection and related project-tool support code
- Affected tests:
  - Gemini headless runtime and launch-plan tests
  - Gemini auth projection or project-tool tests
  - Live/manual validation flow for Gemini CLI
- Affected docs:
  - run-phase backend reference
  - Gemini-related project/tool setup guidance
