# Resume A Pairwise Loop Run

Use this page when the user wants to restore one previously paused pairwise loop.

## Workflow

1. Resolve the designated master and the target `run_id`.
2. Confirm that the run is currently `paused` rather than already `running` or `stopped`.
3. Send one normalized resume request to the master through `houmao-agent-messaging`.
4. Restore the paused wakeup mechanisms for that same run through the owned master and gateway surfaces.
5. Keep the same `run_id` and return the run to `running` when the wakeup posture is active again.

## Resume Contract

- `resume` restores the paused wakeup mechanisms for the same run.
- `resume` is not a synonym for `start`.
- `resume` should not silently widen the participant set, delegation policy, or completion condition.

## Guardrails

- Do not treat `resume` as creation of a brand-new run.
- Do not resume a run that is already `stopped` without explicit re-authoring.
- Do not leave the wakeup posture ambiguous after sending a resume request.
