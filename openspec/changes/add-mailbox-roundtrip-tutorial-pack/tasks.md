## 1. Tutorial Pack Skeleton

- [ ] 1.1 Create `scripts/demo/mailbox-roundtrip-tutorial-pack/` with the required tutorial-pack layout: `README.md`, `run_demo.sh`, `inputs/`, `scripts/`, and `expected_report/`.
- [ ] 1.2 Add tracked tutorial inputs for demo parameters plus the initial and reply message bodies so the roundtrip flow is self-contained.

## 2. Runner And Report Flow

- [ ] 2.1 Implement `run_demo.sh` workspace setup, prerequisite checks, tracked-input copying, and two-agent mailbox-enabled startup with captured `start-session` artifacts.
- [ ] 2.2 Extend the runner to execute `mail send`, recipient `mail check`, `mail reply`, sender `mail check`, and two-session cleanup, using the `message_id` returned by `mail send` as the reply parent.
- [ ] 2.3 Implement raw report generation plus `scripts/sanitize_report.py` and `scripts/verify_report.py`, including `--snapshot-report` support for sanitized expected-report refresh.

## 3. Tutorial Documentation

- [ ] 3.1 Write the tutorial README in the repository's question-first tutorial-pack style, with prerequisites, implementation idea, inline critical inputs and outputs, and explicit command-by-command start/send/check/reply/check/stop steps.
- [ ] 3.2 Document the run/verify/snapshot workflow and appendix details in the README, and update any repo-owned tutorial/demo index links that should surface the new pack.

## 4. Validation

- [ ] 4.1 Add focused automated coverage for report sanitization, verification, and any runner parsing helpers introduced for the mailbox tutorial pack.
- [ ] 4.2 Add demo or integration coverage for the mailbox roundtrip tutorial workflow and expected-report contract.
- [ ] 4.3 Run targeted validation for the new tutorial pack and `openspec validate --strict --json --change add-mailbox-roundtrip-tutorial-pack`.
