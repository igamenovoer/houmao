## 1. `agents mail` Discovery And Routing

- [ ] 1.1 Add `houmao-mgr agents mail resolve-live` and `mark-read` to the managed-agent mail command family
- [ ] 1.2 Implement explicit-selector versus current-session targeting rules for `houmao-mgr agents mail ...`, including manifest-first tmux discovery and clear outside-tmux failure handling
- [ ] 1.3 Implement normalized `resolve-live` output for JSON and shell consumers, including mailbox binding data and live gateway discovery fields

## 2. Manager-Owned Mail Execution

- [ ] 2.1 Extract or add a shared direct mailbox execution layer for local `status`, `check`, `send`, `reply`, and `mark-read`
- [ ] 2.2 Wire local `houmao-mgr agents mail ...` commands to that direct execution layer instead of agent-prompt mediation while preserving pair-owned behavior for pair-managed targets
- [ ] 2.3 Update filesystem mailbox execution and bootstrap code so ordinary workflows no longer depend on `rules/scripts/` as the public execution contract

## 3. Skill And Contract Simplification

- [ ] 3.1 Rewrite projected mailbox system skills to use `houmao-mgr agents mail resolve-live`, gateway HTTP `/v1/mail/*` when available, and `houmao-mgr agents mail ...` fallback when it is not
- [ ] 3.2 Reduce the filesystem mailbox public contract so `rules/` is markdown policy guidance and any published `rules/scripts/` helpers are compatibility or implementation detail
- [ ] 3.3 Update any retained compatibility helper-script surfaces so their docs and usage posture no longer present them as the ordinary agent workflow

## 4. Docs And Regression Coverage

- [ ] 4.1 Update mailbox reference docs and CLI reference docs to document `houmao-mgr agents mail resolve-live`, current-session targeting, gateway-first workflows, and `rules/` as policy guidance
- [ ] 4.2 Add or update unit and integration coverage for `houmao-mgr agents mail resolve-live`, including JSON and shell output plus current-session failure cases
- [ ] 4.3 Add or update regression coverage for manager-owned local `agents mail` execution, explicit `mark-read`, and the removal of local prompt-mediated ordinary mailbox follow-up
