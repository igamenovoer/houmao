## 1. Claude auth bundle surfaces

- [x] 1.1 Extend `houmao-mgr project agents tools claude auth add|set|get` to support the new Claude vendor-auth inputs, including `CLAUDE_CODE_OAUTH_TOKEN`, config-dir import, safe file copying, and redacted bundle reporting.
- [x] 1.2 Extend `houmao-mgr project easy specialist create --tool claude` and the derived credential-bundle path so Claude specialists can persist the OAuth-token lane and config-dir login-state lane without requiring API-key or state-template inputs, while keeping `--claude-state-template-file` as optional bootstrap-only input.
- [x] 1.3 Update the Claude adapter/auth projection contract so `CLAUDE_CODE_OAUTH_TOKEN`, `.credentials.json`, and `.claude.json` are projected through the maintained Claude auth-bundle model.

## 2. Claude runtime bootstrap

- [x] 2.1 Update Claude runtime-home preparation so projected vendor `.claude.json` counts as existing Claude runtime state and missing `claude_state.template.json` does not block that lane.
- [x] 2.2 Ensure unattended Claude bootstrap preserves projected `.credentials.json` and limits its mutations to strategy-owned onboarding, trust, and permission-suppression state.
- [x] 2.3 Add or update runtime/bootstrap coverage for OAuth-token env propagation and imported Claude login-state startup.

## 3. Discovery and operator guidance

- [x] 3.1 Update `src/houmao/agents/assets/system_skills/houmao-create-specialist/SKILL.md` and the Claude credential lookup reference so discovered `CLAUDE_CODE_OAUTH_TOKEN` and maintained Claude config-root login state map into the new Claude create inputs, while `claude_state.template.json` is described only as optional bootstrap state.
- [x] 3.2 Update the primary operator docs, especially `docs/getting-started/easy-specialists.md` and `docs/reference/cli/houmao-mgr.md`, to describe the new Claude vendor-auth lanes and to state clearly that `claude_state.template.json` is optional and not a credential-providing method.
- [x] 3.3 Add or update skill-content regression coverage for the revised Claude discovery/import contract.

## 4. Regression coverage and validation

- [x] 4.1 Add or update CLI tests for `project agents tools claude auth` covering OAuth-token bundles, config-dir imports, patch semantics, and redacted file-backed reporting.
- [x] 4.2 Add or update CLI tests for `project easy specialist create --tool claude` covering the OAuth-token and config-dir lanes without API-key or state-template inputs.
- [x] 4.3 Run focused validation for the touched Claude auth, runtime, skill, and docs surfaces.
