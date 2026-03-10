## Why

The interactive CAO full-pipeline demo can already launch a long-lived session, send prompt turns, and guide operators through manual inspection, but it still lacks a first-class way to send control-key streams through the new runtime-owned `send-keys` path. That gap leaves the tutorial unable to demonstrate slash-command menus, provider navigation, or partial typed input without dropping down to ad hoc commands outside the demo pack.

## What Changes

- Add a dedicated `send-keys` demo command to the CAO interactive full-pipeline workflow instead of overloading the existing `send-turn` prompt path.
- Add a wrapper script for the primary tutorial flow so operators can send raw control-input sequences through the same persisted demo workspace and active session state used by the other wrappers.
- Persist control-input artifacts separately from prompt-turn artifacts so the demo can record what was sent without pretending control input is a prompt/response turn.
- Keep `verify` focused on prompt-turn regression coverage and do not redefine control-input actions as counted turns.
- Update the tutorial and reference workflow docs so operators can discover when to use `send-prompt` versus `send-keys`, including concrete mixed-sequence examples.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `cao-interactive-full-pipeline-demo`: Extend the interactive demo lifecycle with a manifest-driven `send-keys` command that reuses the active session identity and persists control-input artifacts without changing prompt-turn verification semantics.
- `cao-interactive-demo-operator-workflow`: Extend the tutorial workflow and wrapper surface so operators can send manual control-key sequences during the documented interactive CAO journey.

## Impact

- Affected code: `src/gig_agents/demo/cao_interactive_full_pipeline_demo.py`, `scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh`, and a new wrapper script under `scripts/demo/cao-interactive-full-pipeline-demo/`.
- Affected tests: demo CLI integration coverage for the full-pipeline workflow and wrapper behavior around `send-keys`.
- Affected docs/specs: the interactive demo README plus OpenSpec requirements for the interactive demo lifecycle and operator workflow.
- Dependencies: no new external dependency is required; the change reuses the existing runtime `send-keys` support already available for CAO-backed sessions.
