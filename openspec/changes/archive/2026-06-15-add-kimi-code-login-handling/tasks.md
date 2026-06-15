## 1. Skill Routing and Kimi Login Guidance

- [x] 1.1 Add a local Kimi Code login-handling page under `src/houmao/agents/assets/system_skills/houmao-credential-mgr/` that explains `kimi login`, isolated `KIMI_CODE_HOME`, tmux execution, proxy forwarding, default `credentials/kimi-code.json` validation, and `--code-home` import.
- [x] 1.2 Update `houmao-credential-mgr/SKILL.md` so explicit Kimi Code login/import requests route to the new Kimi-specific guidance while Kimi remains outside the maintained `credentials <tool> login` helper list.
- [x] 1.3 Update `actions/login.md` so its Kimi branch points to the Kimi Code login-handling guidance instead of stopping at CRUD-only guidance, while preserving the no-`credentials kimi login` guardrail.

## 2. Kimi Credential Reference Updates

- [x] 2.1 Update `references/kimi-credential-kinds.md` to describe default Kimi Code OAuth as a `kimi login` plus `--code-home` workflow.
- [x] 2.2 Keep Kimi Platform API key guidance mapped to `--api-key` and related Kimi model/provider flags, separate from OAuth login handling.
- [x] 2.3 Document the current scoped-OAuth limitation for non-default `KIMI_CODE_OAUTH_HOST`, `KIMI_OAUTH_HOST`, or `KIMI_CODE_BASE_URL` environments without promising unsupported imports.

## 3. Tests and Validation

- [x] 3.1 Update packaged system-skill tests that currently assert Kimi is CRUD-only so they expect Kimi login-handling guidance without a maintained helper command.
- [x] 3.2 Add assertions that the new Kimi login-handling page includes tmux, isolated `KIMI_CODE_HOME`, proxy forwarding, `kimi login`, `credentials/kimi-code.json`, and `--code-home` import guidance.
- [x] 3.3 Run focused unit tests for packaged system skills and docs guidance.
- [x] 3.4 Run OpenSpec apply-readiness validation for `add-kimi-code-login-handling`.
