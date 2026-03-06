## Why

The repo now has a dedicated CAO server launcher, but there is no self-contained
demo pack showing how to run it end-to-end and verify results reproducibly.
We need a tutorial-pack style demo in `scripts/demo/` so users can copy one
workflow, run one script, and validate behavior against tracked expectations.

## What Changes

- Add a new demo pack under `scripts/demo/` focused on CAO server launcher usage.
- Follow the repo's demo pattern and the tutorial-pack guidance from
  `context/instructions/explain/make-api-tutorial-pack.md`:
  - tracked `inputs/`
  - tracked `expected_report/`
  - `scripts/sanitize_report.py` for deterministic snapshot updates
  - `run_demo.sh` with temp workspace and `--snapshot-report`
  - optional verification helper script for report contract checks
  - step-by-step `README.md` that inlines meaningful run steps and critical outputs
- Cover launcher `status`, `start`, and `stop` with JSON outputs and artifact
  checks (pid/log/result path behavior).
- Ensure the demo is non-destructive and safely skips when prerequisites are
  not available.
- Ensure the README includes complete tutorial sections from the new guidance,
  including critical example code with inline comments and appendix tables.

## Capabilities

### New Capabilities
- `cao-server-launcher`: Self-contained runnable demo pack for CAO
  launcher start/status/stop flows with tracked expected report snapshots.

### Modified Capabilities
- *(none)*

## Impact

- New OpenSpec capability spec under
  `openspec/changes/archive/2026-03-05-cao-server-launcher-demo-pack/specs/`.
- New demo assets under `scripts/demo/` (runner, README, inputs, expected report, scripts).
- Improves operational onboarding and regression confidence for launcher behavior.
