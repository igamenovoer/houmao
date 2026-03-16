## 1. Runner CLI And Demo Layout

- [x] 1.1 Add `--demo-output-dir` parsing to `scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh`, resolve relative paths from the repository root, and change the default demo-owned output root to `tmp/demo/mailbox-roundtrip-tutorial-pack`.
- [x] 1.2 Refactor runner path setup so copied inputs, runtime root, shared mailbox root, captured JSON outputs, and reports all live under the selected demo output directory instead of under one generic workspace path.

## 2. Project Worktree And Jobs Root

- [x] 2.1 Implement nested `project/` worktree provisioning and validation in the mailbox tutorial runner, reusing a valid existing worktree when present and failing clearly when `<demo-output-dir>/project` exists but is not a git worktree.
- [x] 2.2 Launch both agents with `--workdir <demo-output-dir>/project`, keep mailbox root under `<demo-output-dir>/shared-mailbox`, and update any helper/report generation logic that currently assumes the old flat workspace layout.
- [x] 2.3 Add a demo-owned `--jobs-dir <path>` option that resolves relative paths from the repository root and applies the selected jobs-root override through `AGENTSYS_LOCAL_JOBS_DIR`, while preserving the default Houmao job-dir behavior when omitted.

## 3. Documentation And Report Contract

- [x] 3.1 Revise the tutorial README to explain `--demo-output-dir`, the nested `project/` worktree, mailbox/runtime root placement, and default versus overridden job-dir behavior, including the note that the worktree reflects committed repository state.
- [x] 3.2 Update report sanitization, expected-report fixtures, and any appendix/inventory content so demo-output-dir, project worktree, runtime root, mailbox root, and job-dir paths are masked consistently.

## 4. Validation

- [x] 4.1 Extend unit coverage for path resolution, worktree provisioning/validation, and report-sanitization behavior introduced by the new demo-output-dir layout.
- [x] 4.2 Extend subprocess-style runner or integration coverage to exercise the revised output-directory layout, nested project workdir, and optional jobs-dir override behavior.
- [x] 4.3 Run targeted validation for the revised tutorial pack and `openspec validate --strict --json --type change add-mailbox-roundtrip-demo-output-dir`.
