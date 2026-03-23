## 1. Tutorial Pack Skeleton

- [x] 1.1 Create `scripts/demo/mailbox-roundtrip-tutorial-pack/` with the required tutorial-pack layout: `README.md`, `run_demo.sh`, `inputs/`, `scripts/`, and `expected_report/`.
- [x] 1.2 Add tracked tutorial inputs for demo parameters plus the initial and reply message bodies so the roundtrip flow is self-contained, and define the `inputs/demo_parameters.json` schema explicitly: default Claude Code + Codex blueprints, `cao_rest` backend, agent identities, mailbox principal/address pairs, shared mailbox-root template, and message body file references.

## 2. Runner And Report Flow

- [x] 2.1 Implement `run_demo.sh` workspace setup, prerequisite checks, tracked-input copying, and two-agent CAO-backed startup using `build-brain --blueprint` plus `start-session --blueprint --backend cao_rest`, with mailbox enablement expressed through `--mailbox-*` flags and with captured `start-session` artifacts for both agents.
- [x] 2.2 Keep runner state minimal by using shell-local variables plus captured startup artifacts, rely on runtime name-based tmux/manifest recovery for follow-up targeting, and implement cleanup-on-partial-failure plus `trap`-driven teardown so an already-started first session is still stopped if the second startup fails.
- [x] 2.3 Extend the runner to execute `mail send`, recipient `mail check`, `mail reply`, sender `mail check`, and two-session cleanup, always using the correct `--agent-identity` for sender versus receiver and validating that `mail send` returned a non-empty `message_id` before attempting `mail reply`.
- [x] 2.4 Implement raw report generation plus `scripts/sanitize_report.py` and `scripts/verify_report.py`, including `--snapshot-report` support for sanitized expected-report refresh, and explicitly mask concrete non-deterministic fields such as `message_id`, `thread_id`, `request_id`, `bindings_version`, timestamps, runtime roots, manifest paths, and other absolute paths.

## 3. Tutorial Documentation

- [x] 3.1 Write the tutorial README in the repository's question-first tutorial-pack style, with CAO prerequisites, the default Claude Code + Codex blueprint pair, implementation idea, inline critical inputs and outputs, and explicit command-by-command build/start/send/check/reply/check/stop steps.
- [x] 3.2 Document the run/verify/snapshot workflow and appendix details in the README, explain that mailbox config is supplied on `start-session` while credentials come from blueprint-bound recipes, and update any repo-owned tutorial/demo index links that should surface the new pack.

## 4. Validation

- [x] 4.1 Add focused automated coverage for report sanitization, verification, and any runner parsing helpers introduced for the mailbox tutorial pack.
- [x] 4.2 Add subprocess-style demo or integration coverage for the mailbox roundtrip tutorial workflow and expected-report contract, making the exercised runner/report path explicit instead of leaving the coverage shape implicit.
- [x] 4.3 Run targeted validation for the new tutorial pack and `openspec validate --strict --json --type change add-mailbox-roundtrip-tutorial-pack`.
