## 1. Change-Owned Testplans And Runner Surface

- [ ] 1.1 Add and review change-owned case plans under `openspec/changes/add-real-agent-mailbox-roundtrip-autotest/testplans/case-*.md` for the canonical real-agent HTT cases before code changes begin.
- [ ] 1.2 Add `scripts/demo/mailbox-roundtrip-tutorial-pack/autotest/run_autotest.sh` as a dedicated harness with `--case <case-id>` selection and shared result-path orchestration, without adding HTT subcommands to `run_demo.sh`.
- [ ] 1.3 Add pack-local implementation assets under `scripts/demo/mailbox-roundtrip-tutorial-pack/autotest/` so each supported case has `case-*.sh` plus a companion `case-*.md` file with the same basename.
- [ ] 1.4 Add shared shell libraries and reusable helper functions under `scripts/demo/mailbox-roundtrip-tutorial-pack/autotest/helpers/` and source them from the harness or case scripts instead of duplicating common logic.
- [ ] 1.5 Update tutorial-pack documentation to point at `autotest/run_autotest.sh` plus the implemented `autotest/` directory, and explain that the `.md` files are operator-facing companion docs, not copies of the design-phase `openspec/.../testplans/`.

## 2. Real-Agent HTT Execution

- [ ] 2.1 Implement fail-fast preflight for real local `claude` and `codex` binaries, selected credential profiles, demo-output ownership, CAO ownership, and isolated runtime state.
- [ ] 2.2 Implement the `real-agent-roundtrip` case so it starts two actual local agents, performs direct runtime mail send/check/reply/check, and writes machine-readable case evidence.
- [ ] 2.3 Preserve mailbox message files, per-agent mailbox directories, and stable inspection pointers after `stop`, while keeping sanitized verification output separate.

## 3. Supporting Cases And Contract Cleanup

- [ ] 3.1 Implement the `real-agent-preflight` case so it validates prerequisites without starting sessions and fails with explicit blocker output when prerequisites are missing.
- [ ] 3.2 Implement the `real-agent-mailbox-persistence` case so it proves the final canonical mail files remain readable from disk after the run has stopped.
- [ ] 3.3 Repoint the manual real-agent smoke wrapper and direct-live documentation so only the pack-owned `autotest/run_autotest.sh` harness path satisfies the live HTT contract.
