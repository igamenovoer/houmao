# Request Relay Loop Status

Use this page when the user wants one periodic status update from the designated master for a known `run_id`.

## Workflow

1. Resolve the designated master and the target `run_id`.
2. Send one read-only status request to the master through `houmao-agent-messaging`.
3. Ask the master to report the current run state in terms of the reporting contract from `references/reporting-contract.md`.
4. Present the returned state without redefining that status poll as part of the keepalive mechanism.

## Status Contract

Status is observational and does not keep the run alive. The master remains responsible for liveness even when no status request arrives.

At minimum, ask for:

- current run phase
- active relay lanes or owned downstream handoffs
- latest receipt or final-result posture
- completed results so far
- blockers or late conditions
- next planned actions
- current completion-condition posture
- whether a stop condition is currently active or pending

## Guardrails

- Do not treat `status` as a heartbeat requirement for the master.
- Do not mutate route policy, stop posture, or completion condition during an ordinary status request.
- Do not ask the master to summarize every historical detail when the user only asked for current posture.
