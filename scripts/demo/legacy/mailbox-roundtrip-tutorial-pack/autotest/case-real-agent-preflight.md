# `case-real-agent-preflight`

This companion doc describes the implemented pack-local preflight case for the mailbox tutorial pack. The design-phase plan still lives under `openspec/changes/add-real-agent-mailbox-roundtrip-autotest/testplans/`; this file documents the shipped command and result surface.

Run it with:

```bash
scripts/demo/mailbox-roundtrip-tutorial-pack/autotest/run_autotest.sh \
  --case real-agent-preflight \
  --demo-output-dir scripts/demo/mailbox-roundtrip-tutorial-pack/outputs/autotest/preflight-check
```

What it checks:

- `pixi`, `tmux`, `claude`, and `codex` on `PATH`
- credential and config-profile files selected by the tracked mailbox-demo blueprints
- a fresh or safely reusable demo-output directory
- a demo-local loopback CAO contract and matching profile-store ownership
- demo-local jobs and registry roots for isolated runtime state

What it does not do:

- it does not start any sender or receiver sessions
- it does not send or check mail
- it does not call `stop`

Result artifact:

- `<demo-output-dir>/control/testplans/case-real-agent-preflight.result.json`

That JSON records resolved tool paths, participant credential paths, output-root ownership checks, CAO expectations, and any blockers.
