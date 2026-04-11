# Request Generic Loop Graph Status

Use this page when the user wants one periodic status update from the designated master or root run owner for a known `run_id`.

## Workflow

1. Resolve the designated root owner and the target `run_id`.
2. Send one read-only status request to the root owner through `houmao-agent-messaging`.
3. Ask the root owner to report the current run state in terms of the reporting contract from `references/reporting-contract.md`.
4. Present the returned state without redefining that status poll as part of the keepalive mechanism.

## Status Contract

Status is observational and does not keep the run alive. The root owner remains responsible for liveness even when no status request arrives.

At minimum, ask for:

- current run phase
- typed component posture by `component_id` and `component_type`
- active pairwise components and their driver-worker state
- active relay components and their origin/ingress/egress state
- latest receipt or final-result posture per active component
- completed component results so far
- blockers or late conditions
- next planned actions
- current completion-condition posture
- whether a stop condition is currently active or pending

## Guardrails

- Do not treat `status` as a heartbeat requirement for the root owner.
- Do not mutate graph policy, stop posture, component dependencies, or completion condition during an ordinary status request.
- Do not ask the root owner to summarize every historical detail when the user only asked for current posture.
