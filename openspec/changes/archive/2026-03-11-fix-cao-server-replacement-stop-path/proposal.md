## Why

The interactive CAO demo is supposed to deterministically replace any verified local `cao-server` already bound to the fixed loopback target before it starts a fresh run. In practice, that replacement can fail when launcher `stop` is invoked with a fresh runtime root whose artifact directory has not been created yet, causing startup to abort even though the existing loopback service is safe to recycle.

## What Changes

- Harden launcher `stop` so it always returns structured result output even when its runtime artifact directory does not already exist.
- Tighten interactive demo CAO replacement so one bad launcher-stop candidate does not abort the whole verified replacement flow while other known configs may still own the live service.
- Add regression coverage for the fresh-runtime-root stop path and the demo startup flow that must replace an already-healthy fixed-port `cao-server`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cao-server-launcher`: launcher stop behavior will be strengthened so missing artifact directories do not crash stop-result reporting.
- `cao-interactive-demo-startup-recovery`: verified fixed-loopback CAO replacement will keep progressing across known launcher configs instead of failing on the first malformed stop-output candidate.

## Impact

- Affected code: `src/gig_agents/cao/server_launcher.py`, `src/gig_agents/cao/tools/cao_server_launcher.py`, and `src/gig_agents/demo/cao_interactive_demo/cao_server.py`.
- Affected tests: `tests/unit/cao/test_server_launcher.py`, `tests/unit/demo/test_cao_interactive_demo.py`, and possibly interactive-demo integration coverage around fixed-port replacement.
- Affected behavior: startup of `scripts/demo/cao-interactive-full-pipeline-demo/` when a healthy verified `cao-server` is already serving `http://127.0.0.1:9889`.
