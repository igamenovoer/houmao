## Why

`houmao-agent-loop-pairwise-v2` currently distinguishes soft `pause`/`resume` from terminal `hard-kill`, but it does not provide a first-class way to recover one accepted logical run after participants were stopped, killed, or relaunched. Operators have to manually reconstruct run identity, participant bindings, durable memory pointers, mailbox posture, and notifier state across several lower-level surfaces, which is fragile for the long-running pairwise-v2 runs the enriched workflow is meant to support.

## What Changes

- Add `recover_and_continue` as a distinct pairwise-v2 operator action for accepted runs whose participants were stopped, killed, or relaunched and later need to continue the same logical run.
- Introduce a runtime-owned pairwise-v2 recovery record that captures the accepted run contract, participant bindings, durable page references, wakeup posture, and continuation lineage needed for restart recovery without storing mutable state in the authored plan bundle.
- Define standard recovery behavior for participant rebinding, continuation material refresh, master re-acknowledgement, wakeup restoration, and fail-closed recovery when continuity under the prior `run_id` is not safe.
- Clarify lifecycle boundaries so `resume` remains the soft-pause action for a still-live run and `hard-kill` remains terminal rather than an implicit recovery entrypoint.

## Capabilities

### New Capabilities
- `pairwise-v2-run-recovery`: Runtime-owned durable recovery records and `recover_and_continue` workflow for rebinding restarted participants to an accepted logical pairwise-v2 run.

### Modified Capabilities
- `houmao-agent-loop-pairwise-v2-skill`: Add `recover_and_continue` operator vocabulary, recovery-specific observed states, and explicit separation between soft `resume`, restart recovery, and terminal `hard-kill`.

## Impact

- Affected specs: `houmao-agent-loop-pairwise-v2-skill` plus one new recovery capability for pairwise-v2 run restoration.
- Affected systems: pairwise-v2 skill assets, managed-memory page/memo conventions, runtime-owned session state, managed-agent relaunch/rebind flows, and gateway/notifier restoration posture.
- Affected code paths: loop skill assets under `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v2/`, runtime/session state handling, gateway status and notifier control integration, and any new recovery-manifest storage helpers.
- External dependencies: none expected; the change should compose existing runtime manifests, managed memory, and gateway status surfaces.
