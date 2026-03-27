## Why

The current gateway mail wake-up demo pack is anchored to a demo-owned `houmao-server` plus `houmao_server_rest` flow and a single Codex default lane. That no longer matches the desired operator story for this demo, which should teach the serverless `houmao-mgr` workflow, keep all generated state inside the demo directory, and verify the filesystem mailbox contract more directly.

The existing sanitized contract also proves notifier wake-up and output-file side effects more than full mailbox completion. The rewrite should make the demo teach and verify the current serverless mailbox and gateway seams for both Claude Code and Codex.

## What Changes

- Rewrite `scripts/demo/gateway-mail-wakeup-demo-pack/` around serverless `houmao-mgr` managed-agent commands instead of demo-owned `houmao-server` and `backend=houmao_server_rest`.
- Change the demo to support separate Claude Code and Codex runs while keeping one live agent per run.
- Move all generated demo-owned artifacts under the pack directory, including runtime, registry, jobs, deliveries, copied project, output files, and the filesystem mailbox root.
- Update the automatic and manual workflows to use the serverless mailbox lifecycle: mailbox init, agent launch, mailbox registration, gateway attach, notifier enable, managed filesystem mail delivery, inspect, verify, and stop.
- Update verification so the demo proves filesystem mailbox contract completion through gateway and mailbox evidence, including processed-message read state, rather than only file-side effects.
- Refresh the README, expected report contract, and automated coverage to match the new serverless flow and pack-local output ownership model.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `gateway-mail-wakeup-demo-pack`: rewrite the demo contract from pair-managed single-tool wake-up to a serverless `houmao-mgr` workflow with per-tool Claude/Codex coverage, pack-local artifact ownership, and stronger filesystem mailbox verification.

## Impact

- Affected demo pack: `scripts/demo/gateway-mail-wakeup-demo-pack/`
- Likely affected implementation modules: a new or rewritten `src/houmao/demo/gateway_mail_wakeup_demo_pack/` package plus the pack wrapper scripts
- Likely affected tests: unit coverage for the demo pack and live or autotest coverage for Claude/Codex tool lanes
- Likely affected tracked fixtures: agent-definition defaults under `tests/fixtures/agents/` if the demo needs explicit serverless Claude/Codex credential-profile selection
- Affected documentation: the demo README and any references that currently describe the old pair-managed wake-up flow
