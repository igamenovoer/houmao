# `case-real-agent-mailbox-persistence`

This companion doc describes the implemented post-stop mailbox-persistence audit case. The design-phase testplan still lives under `openspec/changes/add-real-agent-mailbox-roundtrip-autotest/testplans/`; this file explains the shipped case entrypoint and evidence.

Run it with:

```bash
scripts/demo/mailbox-roundtrip-tutorial-pack/autotest/run_autotest.sh \
  --case real-agent-mailbox-persistence \
  --demo-output-dir scripts/demo/mailbox-roundtrip-tutorial-pack/outputs/autotest/post-stop-audit
```

Executed flow:

1. Run preflight against the selected live-agent prerequisites.
2. Execute the full start, roundtrip, verify, and stop sequence.
3. Re-open the sender mailbox directory, receiver mailbox directory, and canonical send/reply Markdown message files from disk after stop has completed.
4. Fail the case if any of those post-stop artifacts are missing or unreadable.

Primary artifacts:

- `<demo-output-dir>/control/testplans/case-real-agent-mailbox-persistence.preflight.json`
- `<demo-output-dir>/control/testplans/case-real-agent-mailbox-persistence.result.json`
- `<demo-output-dir>/control/testplans/logs/case-real-agent-mailbox-persistence/`

Use the result JSON when you want the exact mailbox and message paths for manual inspection without re-running the demo.
