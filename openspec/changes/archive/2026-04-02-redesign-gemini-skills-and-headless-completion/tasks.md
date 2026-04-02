## 1. Gemini mailbox skill contract

- [x] 1.1 Update mailbox skill projection helpers and brain-build/runtime code so maintained Gemini mailbox skills install as top-level Houmao-owned directories under `.agents/skills/` instead of `.agents/skills/mailbox/`.
- [x] 1.2 Update runtime-owned Gemini mailbox and notifier prompt construction to invoke installed Houmao mailbox skills by name rather than directing Gemini to open raw `SKILL.md` paths for ordinary mailbox work.
- [x] 1.3 Remove or rewrite maintained Gemini-specific tests, fixtures, and docs that still assume the old `.agents/skills/mailbox/...` contract.

## 2. Headless terminal-turn semantics

- [x] 2.1 Update tmux-backed native headless runtime control so terminal turn status is finalized from managed child-process exit plus durable exit-status artifacts.
- [x] 2.2 Reconcile managed-agent headless detail and related inspection/reporting helpers from authoritative active-turn state plus durable terminal artifacts, with `completion_source` treated as optional diagnostic metadata.
- [x] 2.3 Add or update focused tests for Gemini/Codex/Claude headless terminal-turn reconciliation, including cases where durable terminal artifacts exist before stale live posture settles.

## 3. Demo alignment

- [x] 3.1 Update the single-agent gateway wake-up headless demo so the Gemini lane exercises the native installed Gemini mailbox skill contract rather than a project-local mailbox-skill mirror.
- [x] 3.2 Update demo verification to wait for settled gateway and headless terminal evidence instead of snapshotting a transient in-between state after side effects appear.
- [x] 3.3 Refresh the demo’s tracked expected reports, parameters, and regression coverage to match the new Gemini skill and headless completion contracts.

## 4. Validation and documentation

- [x] 4.1 Update mailbox, Gemini backend, and managed-agent detail reference docs so they describe the new Gemini native-skill contract and process-exit terminality rule.
- [x] 4.2 Run targeted unit/integration/demo validation for Gemini mailbox wake-up, managed-agent detail reconciliation, and the single-agent gateway wake-up headless demo.
