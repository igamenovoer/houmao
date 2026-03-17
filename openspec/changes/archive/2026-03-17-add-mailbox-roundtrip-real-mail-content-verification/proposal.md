## Why

The mailbox roundtrip tutorial-pack automation currently proves command sequencing and sanitized report outputs, but its fast integration harness can still pass without writing real canonical message content into the demo mailbox. That leaves maintainers unable to inspect the actual on-disk send and reply artifacts after an automated run, even though the demo is supposed to exercise a real mailbox roundtrip.

## What Changes

- Revise mailbox roundtrip demo automation coverage so successful automated roundtrip runs leave real filesystem-mailbox message content under the selected demo output directory.
- Extend the mailbox demo verification surface to capture stable evidence about canonical delivered messages, mailbox projections, and thread linkage without turning the sanitized expected report into a content snapshot.
- Update the pack-local scenario runner and related integration tests to assert that the send and reply bodies match the tracked tutorial input files and are inspectable after the run.
- Preserve the current fast automation model where possible by reusing the managed filesystem mailbox delivery stack instead of requiring a fully live external mailbox deployment.

## Capabilities

### New Capabilities
- `mailbox-roundtrip-demo-real-mail-content`: Defines the requirement that mailbox roundtrip demo automation produces inspectable canonical mailbox message content and regression evidence for the sent and replied messages.

### Modified Capabilities
<!-- None. -->

## Impact

- Affected code: `scripts/demo/mailbox-roundtrip-tutorial-pack/scripts/tutorial_pack_helpers.py`, `scripts/demo/mailbox-roundtrip-tutorial-pack/scripts/run_automation_scenarios.py`, `tests/integration/demo/test_mailbox_roundtrip_tutorial_pack_runner.py`, and any shared mailbox test helpers needed to drive managed delivery.
- Affected systems: mailbox roundtrip demo automation, filesystem mailbox artifact inspection, sanitized verification/report boundaries, and maintainer-oriented regression evidence.
- Affected workflow: maintainers will be able to inspect real send/reply content under `<demo-output-dir>/shared-mailbox/` after automated demo runs instead of relying only on synthetic JSON step results.
