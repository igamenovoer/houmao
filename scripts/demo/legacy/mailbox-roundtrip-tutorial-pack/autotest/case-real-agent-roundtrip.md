# `case-real-agent-roundtrip`

This companion doc describes the implemented canonical real-agent HTT case. The design-phase testplan remains under `openspec/changes/add-real-agent-mailbox-roundtrip-autotest/testplans/`; this file documents the shipped pack-local runner.

Run it with:

```bash
scripts/demo/mailbox-roundtrip-tutorial-pack/autotest/run_autotest.sh \
  --case real-agent-roundtrip \
  --demo-output-dir scripts/demo/mailbox-roundtrip-tutorial-pack/outputs/autotest/real-roundtrip
```

Executed flow:

1. Run the same fail-fast preflight used by the other real-agent cases.
2. Start the sender and receiver through `run_demo.sh start`.
3. Print pack-local `inspect` commands before the first live mail turn.
4. Run `run_demo.sh roundtrip`.
5. Run `run_demo.sh verify`.
6. Run `run_demo.sh stop`.
7. Re-open the mailbox artifacts from disk and record the final send/reply evidence.

Primary artifacts:

- `<demo-output-dir>/control/testplans/case-real-agent-roundtrip.preflight.json`
- `<demo-output-dir>/control/testplans/case-real-agent-roundtrip.result.json`
- `<demo-output-dir>/control/testplans/logs/case-real-agent-roundtrip/`

The result JSON records the selected demo root, inspect commands, verify/stop outputs, sender and receiver mailbox directories, and the canonical send/reply Markdown message paths that remain on disk after stop.
