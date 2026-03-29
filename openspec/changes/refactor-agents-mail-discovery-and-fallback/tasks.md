## 1. `agents mail` Discovery And Routing

- [ ] 1.1 Add `houmao-mgr agents mail resolve-live` and `mark-read` to the managed-agent mail command family
- [ ] 1.2 Implement explicit-selector versus current-session targeting rules for `houmao-mgr agents mail ...`, including manifest-first tmux discovery and clear outside-tmux failure handling
- [ ] 1.3 Implement normalized `resolve-live` output for JSON and shell consumers, including mailbox binding data and live gateway discovery fields

## 2. Authority-Aware Local Mail Execution

- [ ] 2.1 Extend verified local mailbox execution where practical for current-session and manager-owned `send`, `reply`, and `mark-read` workflows while preserving existing verified `status` and `check` behavior
- [ ] 2.2 Keep pair-owned and gateway-backed verified execution intact, and preserve the non-authoritative TUI submission result contract where verified direct or gateway authority is still unavailable
- [ ] 2.3 Update filesystem mailbox execution and bootstrap code so ordinary workflows no longer depend on `rules/scripts/` as the public execution contract

## 3. Skill And Contract Simplification

- [ ] 3.1 Rewrite projected mailbox system skills to use `houmao-mgr agents mail resolve-live`, gateway HTTP `/v1/mail/*` when available, and `houmao-mgr agents mail ...` fallback when it is not
- [ ] 3.2 Teach projected mailbox skills to treat `authoritative: false` manager fallback results as submission-only and to verify outcome through manager-owned or transport-owned state
- [ ] 3.3 Reduce the filesystem mailbox public contract so `rules/` is markdown policy guidance and any published `rules/scripts/` helpers are compatibility or implementation detail

## 4. Docs And Regression Coverage

- [ ] 4.1 Update mailbox reference docs and CLI reference docs to document `houmao-mgr agents mail resolve-live`, current-session targeting, gateway-first workflows, verification guidance for non-authoritative fallback, and `rules/` as policy guidance
- [ ] 4.2 Add or update unit and integration coverage for `houmao-mgr agents mail resolve-live`, including JSON and shell output plus current-session failure cases
- [ ] 4.3 Add or update regression coverage for verified local `agents mail` paths, explicit `mark-read`, current-session targeting, and preserved non-authoritative fallback semantics where direct authority is still unavailable
