## Why

The mailbox roundtrip tutorial pack is implemented and already has basic unit and integration coverage, but its automation surface is still shaped around one all-in-one `run_demo.sh` flow plus test-only harness code. That makes automatic hack-through testing awkward: we cannot cleanly drive stepwise reruns, inject failures at meaningful demo phases, or keep the automation assets owned by the same demo directory operators already use.

## What Changes

- Add demo-owned automation commands and helper scripts under `scripts/demo/mailbox-roundtrip-tutorial-pack/` so scripted verification and hack-through-style execution live with the interactive mailbox demo itself.
- Refactor the mailbox roundtrip demo wrapper from one monolithic path into a command surface that supports automated start, roundtrip execution, verification, and cleanup without forcing every automation caller to reimplement demo state handling.
- Add pack-local automation helpers that can run stable scenario checks, archive artifacts under the demo output directory, and exercise failure-oriented cases needed for hack-through testing.
- Extend the tutorial README and report contract so the new automation entrypoints, artifact layout, and intended operator-versus-maintainer usage remain explicit.
- Add integration and manual coverage for the new automation scripts, including default job-dir behavior, rerun/worktree reuse, cleanup on failure or interruption, and explicit verification or snapshot flows.

## Capabilities

### New Capabilities
- `mailbox-roundtrip-demo-automation`: Defines the demo-owned automation commands, helper scripts, scenario execution model, and artifact expectations for the mailbox roundtrip tutorial pack.

### Modified Capabilities
<!-- None. -->

## Impact

- Affected code: `scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh`, new or expanded helper scripts under `scripts/demo/mailbox-roundtrip-tutorial-pack/scripts/`, the pack README, expected-report assets, and related test coverage.
- Affected systems: mailbox demo automation flow, demo-local artifact capture, cleanup and rerun behavior, and maintainer-oriented verification workflows for hack-through testing.
- Affected operator workflow: operators and maintainers will be able to drive pack-local automation from the demo directory itself instead of relying on scattered external harnesses or one-shot wrapper behavior only.
