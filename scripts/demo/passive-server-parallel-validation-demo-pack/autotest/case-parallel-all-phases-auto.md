# `parallel-all-phases-auto`

Run the full Step 7 validation workflow in unattended mode.

## Steps

1. Run `autotest/run_autotest.sh --case parallel-all-phases-auto --demo-output-dir <path>`.
2. Let the runner execute `start -> inspect -> gateway -> headless -> stop -> verify`.
3. Review `<path>/report.json`, `<path>/report.sanitized.json`, and the per-phase logs under `<path>/logs/autotest/`.

## Success Criteria

- Both authorities start successfully against one shared runtime and registry root.
- The shared interactive agent is visible on both authorities and the normalized parity checks pass.
- The passive-server gateway prompt produces observable progress on both authorities.
- The passive-server headless launch becomes visible from the old server.
- Stopping the shared interactive agent through the passive server removes it from both authorities.
- Verification passes against the tracked sanitized expected report.

