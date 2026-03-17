## 1. Command Surface And Helper Orchestration

- [x] 1.1 Refactor `scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh` to expose the pack-local `auto`, `start`, `roundtrip`, `verify`, and `stop` command surface while preserving the one-shot default path.
- [x] 1.2 Extend `scripts/demo/mailbox-roundtrip-tutorial-pack/scripts/tutorial_pack_helpers.py` with the stepwise orchestration, reusable demo-local state handling, and cleanup logic needed by those commands.

## 2. Pack-Local Automation Scripts And Documentation

- [x] 2.1 Add pack-local scenario automation script(s) under `scripts/demo/mailbox-roundtrip-tutorial-pack/scripts/` that execute named scenarios and write machine-readable summaries plus per-scenario outputs under a caller-selected automation root.
- [x] 2.2 Update the mailbox roundtrip pack README and any pack-local artifact inventory or usage guidance so the new maintainer automation entrypoints and output layout are documented from the demo directory itself.

## 3. Verification And Artifact Contracts

- [x] 3.1 Update the demo verification flow so `verify` and `--snapshot-report` work after both one-shot and stepwise automation runs while preserving the sanitized expected-report contract.
- [x] 3.2 Preserve or revise the demo-output-dir artifact contract so stepwise runs, scenario automation, and partial-failure cleanup all leave diagnosable demo-local outputs without conflating unrelated runs.

## 4. Automated Coverage And Validation

- [x] 4.1 Extend integration coverage to drive the pack-local automation scripts for default implicit jobs-dir behavior, explicit jobs-dir override, rerun/worktree reuse, incompatible existing project directories, and cleanup ownership behavior.
- [x] 4.2 Add targeted maintainer-oriented automation coverage for failure or interruption paths through the pack-local scripts, using hermetic fake-tool scenarios where appropriate.
- [x] 4.3 Run targeted mailbox demo tests plus `pixi run openspec validate --strict --json --type change add-mailbox-roundtrip-demo-automation-scripts`.
