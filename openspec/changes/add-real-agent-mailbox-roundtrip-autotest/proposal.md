## Why

The mailbox roundtrip tutorial pack currently splits its automation story between deterministic stand-in coverage and an opt-in manual smoke script. That split does not satisfy hack-through-testing: the canonical end-to-end path still is not a pack-owned, non-interactive run that uses actual local agents, actual credential profiles, real mailbox delivery, and inspectable on-disk mail artifacts.

Maintainers need one explicit real-agent autotest path that fails fast when local prerequisites are missing, drives one actual sender-to-receiver roundtrip, and leaves the final mailbox files on disk so the completed mail can be inspected after the run.

## What Changes

- Add a pack-owned real-agent HTT harness script for `scripts/demo/mailbox-roundtrip-tutorial-pack` that uses actual local `claude` and `codex` executables plus real credential profiles without overloading `run_demo.sh`.
- Define one canonical HTT case that performs `start -> mail send -> mail check -> mail reply -> mail check -> verify -> stop` and preserves the resulting mailbox files under the selected demo output root.
- Add fail-fast preflight checks, bounded timeout behavior, and machine-readable autotest evidence so the real-agent path surfaces the next blocker instead of silently hanging or falling back to synthetic success.
- Treat `openspec/changes/add-real-agent-mailbox-roundtrip-autotest/testplans/case-*.md` as design-phase artifacts only, and use those approved case plans to drive later pack-local implementation assets under `scripts/demo/mailbox-roundtrip-tutorial-pack/autotest/`.
- Require each implemented pack-local test case to ship as a same-basename pair under `autotest/`: `autotest/case-*.sh` for the executable case steps and `autotest/case-*.md` as the operator-facing companion/readme for that implemented case.
- Put shared autotest shell libraries and reusable helper functions under `scripts/demo/mailbox-roundtrip-tutorial-pack/autotest/helpers/` so case scripts do not duplicate common behavior.
- Route case selection through a separate `scripts/demo/mailbox-roundtrip-tutorial-pack/autotest/run_autotest.sh` harness that dispatches into the implemented `autotest/case-*.sh` files instead of bundling HTT execution into `run_demo.sh` subcommands.
- Reclassify fake-cli or stand-in mailbox runs as non-canonical regression aids; they may remain useful, but they must not claim to satisfy the real-agent direct-live HTT contract.

## Capabilities

### New Capabilities

- `mailbox-roundtrip-real-agent-autotest`: pack-owned hack-through-testing automation for running the mailbox roundtrip with actual local agents, real credentials, fail-fast preflight, and inspectable mailbox artifacts, using a dedicated harness script plus design-phase case plans tracked under the OpenSpec change.

### Modified Capabilities

- `mailbox-roundtrip-tutorial-pack`: the pack layout and documentation will include pack-local `autotest/` implemented case scripts plus companion readme-style Markdown, and identify the canonical HTT path.
- `mailbox-roundtrip-demo-automation`: the pack automation surface will grow a dedicated real-agent autotest harness script and case selection path that is separate from `run_demo.sh`.
- `mailbox-roundtrip-direct-live-automation-test`: the direct-live contract will explicitly require actual local tool binaries and real credential resolution rather than deterministic stand-ins.

## Impact

- Affected code: `scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh`, `scripts/demo/mailbox-roundtrip-tutorial-pack/autotest/run_autotest.sh`, `scripts/demo/mailbox-roundtrip-tutorial-pack/scripts/tutorial_pack_helpers.py`, pack-local automation helpers, and the manual real-agent smoke wrapper under `tests/manual/`.
- Affected planning/docs: `openspec/changes/add-real-agent-mailbox-roundtrip-autotest/testplans/`, `scripts/demo/mailbox-roundtrip-tutorial-pack/README.md`, and later pack-local `autotest/case-*.md`, `autotest/case-*.sh`, and `autotest/helpers/` assets during implementation.
- Affected tests and verification: pack-local scenario ownership, real-agent smoke/autotest flows, and any direct-live claims in integration/manual coverage.
- Affected operational prerequisites: local `claude` and `codex` executables, tracked credential profiles, owned loopback CAO state, and deterministic demo-output artifact retention.
