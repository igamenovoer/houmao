## 1. Demo Pack Scaffold

- [x] 1.1 Create new demo directory under `scripts/demo/` with `inputs/`, `expected_report/`, and `scripts/`
- [x] 1.2 Add initial tracked input files describing launcher config/demo parameters
- [x] 1.3 Add initial tracked expected report snapshot file

## 2. Runner + Verification

- [x] 2.1 Implement `run_demo.sh` with robust shell defaults, temp workspace setup, and prerequisite checks
- [x] 2.2 Implement tracked-input copy from demo pack into workspace before launcher commands
- [x] 2.3 Implement launcher flow in runner (`status`, `start`, post-start `status`, `stop`, post-stop `status`) and collect JSON outputs
- [x] 2.4 Add `scripts/sanitize_report.py` to normalize non-deterministic fields in generated reports
- [x] 2.5 Build report generation and `--snapshot-report` behavior that writes sanitized content into `expected_report/`
- [x] 2.6 Add optional verification helper (if needed) to compare sanitized report against expected snapshot

## 3. Documentation

- [x] 3.1 Write `README.md` with title/question, prerequisites, and implementation idea
- [x] 3.2 Add critical example code blocks with rich inline comments (launcher CLI usage)
- [x] 3.3 Inline critical input/output snippets in README (not path-only references)
- [x] 3.4 Document explicit step-by-step run/verify flow mirroring meaningful runner actions
- [x] 3.5 Add snapshot refresh and troubleshooting guidance
- [x] 3.6 Add appendix table for key parameters plus full input/output file inventory

## 4. Validation

- [x] 4.1 Run demo once to verify end-to-end behavior and adjust sanitization rules
- [x] 4.2 Run demo with `--snapshot-report` to refresh/confirm sanitized expected report contract
- [x] 4.3 Re-run demo to confirm verification against refreshed expected report
- [x] 4.4 Lint shell/python helper files used by the new demo pack
