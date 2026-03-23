## Why

Managed headless agents in `houmao-server` are intended to be controller-owned, action-driven runtimes, but the current reconciliation path still infers turn truth from tmux window presence. That leaks TUI watch-plane assumptions into headless execution and can incorrectly mutate active or completed headless turns into `unknown` or other degraded states even when the underlying CLI tool is still running or has already produced durable output.

## What Changes

- Change managed headless turn lifecycle authority so normal turn status is derived from CLI execution results, machine-readable output, durable turn artifacts, and explicit server-owned interrupt intent rather than tmux window or pane observation.
- Persist runner-owned durable process metadata for managed headless turns so restart recovery and interrupt handling can rely on execution identity rather than tmux watching.
- Normalize managed headless no-evidence terminal outcomes to explicit failure-with-diagnostic semantics instead of treating `unknown` as a normal public result.
- Tighten managed headless restart and reconciliation behavior so unexpected process death is treated as normal execution failure or interruption handling, not as a TUI-style watch event.
- Clarify that tmux remains a headless execution container, inspection surface, and best-effort control transport, but not the authoritative source of headless turn outcome.
- Update managed headless state and detail semantics so callers can reason about operability and last-turn outcomes from server-owned execution evidence without relying on tmux watching.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `houmao-server-agent-api`: managed headless turn submission, reconciliation, interrupt, restart recovery, and turn inspection semantics change to rely on CLI-owned execution evidence rather than tmux watching.
- `managed-agent-detailed-state`: managed headless detailed-state posture changes to reflect controller-owned execution evidence and treat tmux liveness as auxiliary diagnostic information rather than turn-truth authority.

## Impact

- Affected code: `src/houmao/server/service.py`, `src/houmao/server/managed_agents.py`, `src/houmao/server/models.py`, and `src/houmao/agents/realm_controller/backends/headless_runner.py`
- Affected tests: managed headless unit and integration coverage under `tests/unit/server/`, `tests/unit/agents/realm_controller/`, and demo flows that currently exercise managed headless reconciliation and reporting
- Affected behavior: headless turn status vocabulary, restart reconciliation, interrupt fallback semantics, durable execution evidence, and detailed managed-agent state for headless agents
