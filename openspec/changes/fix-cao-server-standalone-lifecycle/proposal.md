## Why

The interactive CAO demo currently depends on a fixed loopback `cao-server` remaining reachable across later `inspect`, `send-turn`, and `send-keys` commands, but the current launcher only proves that the server became healthy once during startup. In practice, the tmux-backed agent session can remain alive while the CAO REST API disappears, which breaks the demo's runtime contract and makes agent recreation nondeterministic.

## What Changes

- **BREAKING**: Change `cao-server` launcher startup semantics so `start` creates a standalone detached `cao-server` service rather than a parent-lifetime-bound subprocess.
- Extend launcher-managed artifacts to describe standalone service ownership and support later verification, status, and stop operations against that detached process.
- **BREAKING**: Change interactive CAO demo startup so recreating an agent on the fixed loopback target force-replaces any verified local `cao-server` instead of prompting to reuse or keep it.
- Update launcher and interactive-demo docs, reports, and tests to reflect standalone-service lifecycle and deterministic replacement behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cao-server-launcher`: launcher lifecycle requirements change from "start or reuse a background process" to "bootstrap and manage a standalone detached CAO service with ownership metadata".
- `cao-interactive-demo-startup-recovery`: interactive demo startup requirements change from confirmation-gated replacement to deterministic force-replacement of the verified fixed-port CAO service during agent recreation.
- `cao-server-launcher-demo-pack`: the launcher tutorial-pack requirements change to validate the standalone-service contract and updated launcher artifacts/report shape.

## Impact

- Affected code: `src/gig_agents/cao/server_launcher.py`, `src/gig_agents/cao/tools/cao_server_launcher.py`, `src/gig_agents/demo/cao_interactive_demo/cao_server.py`, and interactive demo command/startup wiring.
- Affected demos/docs: `scripts/demo/cao-server-launcher/`, `scripts/demo/cao-interactive-full-pipeline-demo/`, and related reference docs under `docs/reference/`.
- Affected tests: launcher unit/integration coverage, interactive demo integration coverage, and demo expected reports that encode launcher artifact and replacement behavior.
