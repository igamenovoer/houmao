# Resume A Pairwise Loop Run

Use this page when the user wants to restore one previously paused pairwise loop.

## Workflow

1. Resolve the designated master and the target `run_id`.
2. Confirm that the run is currently `paused` rather than already `running`, `recovering`, or `stopped`.
3. Confirm that the participant set and wakeup posture remained logically live while the run was paused:
   - if one or more participants were stopped, killed, or relaunched, use `recover_and_continue` instead
   - if the runtime-owned recovery record already shows restart-recovery work in progress, stay in that lane instead of collapsing it into `resume`
4. Send one normalized resume request to the master through `houmao-agent-messaging`.
5. Restore the paused wakeup mechanisms for that same run through the owned master and gateway surfaces.
6. Keep the same `run_id` and return the run to `running` when the wakeup posture is active again.

## Resume Contract

- `resume` restores the paused wakeup mechanisms for the same run.
- `resume` is not a synonym for `start`.
- `resume` is pause-only; stopped, killed, or relaunched participants require `recover_and_continue`.
- `resume` should not silently widen the participant set, delegation policy, or completion condition.

## Guardrails

- Do not treat `resume` as creation of a brand-new run.
- Do not use `resume` to recover participants that were stopped, killed, or relaunched.
- Do not resume a run that is already `stopped` without explicit re-authoring or the restart-recovery flow.
- Do not leave the wakeup posture ambiguous after sending a resume request.
