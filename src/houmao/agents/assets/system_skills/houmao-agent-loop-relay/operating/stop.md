# Stop A Relay Loop Run

Use this page when the user wants to stop one active relay loop run owned by the designated master.

## Workflow

1. Resolve the designated master and the target `run_id`.
2. Determine stop mode:
   - `interrupt-first` by default
   - graceful stop only when the user explicitly requests graceful termination
3. Send one normalized stop request to the master through `houmao-agent-messaging`.
4. Tell the master what stop means for this run:
   - stop opening new downstream work
   - preserve already-returned partial results
   - summarize what completed, what was interrupted, and what remains unfinished
5. For the default interrupt-first mode, tell the master to interrupt active downstream relay work first and then reconcile returned state.
6. For explicit graceful stop, tell the master to stop creating new work and drain according to the user's requested graceful posture.

## Default Stop Posture

`interrupt-first` is the default stop posture for this skill. Do not switch to graceful termination unless the user explicitly requests it.

## Guardrails

- Do not default to graceful stop.
- Do not leave the stop mode implicit when sending the stop request.
- Do not ask the user agent to interrupt every downstream agent individually; the stop signal goes to the master.
- Do not discard already-returned partial results when stopping the run.
