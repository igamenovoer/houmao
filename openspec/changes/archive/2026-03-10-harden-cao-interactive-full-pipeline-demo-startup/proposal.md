## Why

The interactive CAO full-pipeline demo is no longer fully reliable in real local environments where `http://127.0.0.1:9889` is already occupied by a valid `cao-server` or where procfs inspection hits unreadable `/proc/*/fd` entries. We need to harden demo startup so the wrapper flow keeps working under the same fixed-port contract it already advertises.

## What Changes

- Tighten interactive demo startup recovery so replacing an already-verified local loopback `cao-server` works reliably from the wrapper flow, including the `-y` non-interactive path.
- Require fixed-port occupant verification and replacement logic to tolerate permission-restricted procfs entries instead of crashing during `/proc` traversal.
- Clarify that startup must only fail for truly unverifiable loopback occupants, not because unrelated `/proc` entries are unreadable while validating a verified local `cao-server`.
- Refresh demo startup integration coverage to exercise verified replacement and procfs-permission edge cases under the wrapper scripts.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cao-interactive-demo-startup-recovery`: Harden fixed-loopback CAO replacement and process-verification requirements so interactive demo startup remains reliable with an existing verified local `cao-server` and under permission-restricted procfs traversal.

## Impact

- Affected code: `src/gig_agents/demo/cao_interactive_full_pipeline_demo.py` and demo wrapper or integration-test support around `scripts/demo/cao-interactive-full-pipeline-demo/`.
- Affected tests: `tests/integration/demo/test_cao_interactive_full_pipeline_demo_cli.py` and related startup-focused demo tests.
- Affected systems: local fixed-port CAO startup and replacement behavior for the interactive full-pipeline demo.
