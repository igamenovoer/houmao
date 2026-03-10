## 1. Startup Recovery Hardening

- [x] 1.1 Keep the interactive demo's verified fixed-loopback replacement path on launcher-managed stop/start flow when launcher status already proves a healthy local `cao-server`.
- [x] 1.2 Harden procfs fallback verification in `cao_interactive_full_pipeline_demo.py` so unreadable or disappearing `/proc/<pid>/fd` entries are skipped instead of crashing startup.
- [x] 1.3 Preserve explicit failure diagnostics when the fixed-loopback occupant still cannot be safely verified as `cao-server` after the best-effort fallback path.

## 2. Demo Regression Coverage

- [x] 2.1 Update interactive demo wrapper integration coverage so verified replacement scenarios remain deterministic even when the host machine already has a real listener on `127.0.0.1:9889`.
- [x] 2.2 Add regression coverage for procfs-permission edge cases, including unreadable `/proc/<pid>/fd` traversal during fallback verification.
- [x] 2.3 Run focused demo validation for `tests/unit/demo/test_cao_interactive_full_pipeline_demo.py` and `tests/integration/demo/test_cao_interactive_full_pipeline_demo_cli.py`.
