## Why

The current mailbox roundtrip automation can pass while relying on a hermetic fake harness, which means maintainers still cannot trust it as proof that the real tutorial pack starts two live agents, drives direct mailbox operations, and leaves readable mail on disk. We now need automatic coverage for the real code path because the live demo currently exposes failures that the fake harness hides.

## What Changes

- Add automatic test coverage for `scripts/demo/mailbox-roundtrip-tutorial-pack` that uses a fresh demo output directory, starts two real agents, and exercises the real mailbox roundtrip path end to end through an owned automatic workflow target. That target may be a dedicated integration test, a scripted runner, or another multi-step automatic sequence over the demo directory.
- Require successful automatic runs to leave two inspectable per-agent mailbox directories plus canonical Markdown message documents that a maintainer can open and read after the test.
- Require the automatic test to use the direct live-agent mail path (`run_demo.sh roundtrip`, `realm_controller mail ...`, or equivalent direct prompt execution), not fake mailbox injection and not gateway transport commands such as `attach-gateway` or `gateway-send-prompt`.
- Isolate automatic runs from ambient local state by using a test-owned loopback CAO instance, fresh output roots, and an isolated shared-registry root so the test may stop and restart its own CAO safely.
- Preserve sanitized report verification as a separate concern from the raw inspectable mailbox artifacts.

## Capabilities

### New Capabilities
- `mailbox-roundtrip-direct-live-automation-test`: Defines automatic testing requirements for the mailbox roundtrip tutorial pack using real started agents, direct live mailbox operations, isolated owned runtime state, and inspectable on-disk mailbox artifacts.

### Modified Capabilities
<!-- None. -->

## Impact

- Affected code: `scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh`, `scripts/demo/mailbox-roundtrip-tutorial-pack/scripts/tutorial_pack_helpers.py`, `tests/integration/demo/test_mailbox_roundtrip_tutorial_pack_runner.py`, and likely new live integration coverage under `tests/integration/demo/`.
- Affected systems: CAO launcher ownership and restart behavior, shared-registry isolation, runtime session startup/readiness, direct `realm_controller mail` execution, and filesystem mailbox inspection.
- Affected workflow: automatic demo verification will move beyond contract-only fake-harness checks and must prove that maintainers can inspect two real mailbox views and read the generated mail content after a successful run, whether the automation target is expressed as a test case or a multi-step owned demo workflow.
