# Peek A Pairwise Loop Run

Use this page when the user wants canonical read-only inspection of one pairwise loop run through `peek master`, `peek all`, or `peek <agent-name>`.

## Workflow

1. Resolve the target `run_id` plus one selector:
   - `master`
   - `all`
   - one selected participant name
2. Keep `peek` read-only and unintrusive. Do not turn it into a fresh progress prompt or job communication message.
3. Route inspection through `houmao-agent-inspect`:
   - `peek master`: inspect the designated master's current run posture, visible artifacts, mailbox posture, or gateway-backed state for the run
   - `peek all`: inspect the master plus each current participant and aggregate the visible run posture
   - `peek <agent-name>`: inspect only that selected participant
4. Summarize the returned posture using the reporting contract in `references/reporting-contract.md`.
5. Use the canonical observed states when describing the current run:
   - `running`
   - `paused`
   - `stopping`
   - `stopped`
   - `dead`
   - or the relevant earlier prestart states when the run has not yet begun
6. If the read-only surfaces are insufficient and the user wants an active question answered, switch to `ping <agent-name>` instead of redefining `peek`.

## Peek Contract

- `peek` is observational.
- `peek` is unintrusive inspection; it does not ask agents to do work, acknowledge work, or report progress through a new prompt.
- `peek` does not keep the run alive.
- `peek master`, `peek all`, and `peek <agent-name>` are the canonical selectors.

## Guardrails

- Do not send a fresh prompt merely to satisfy `peek`.
- Do not send email or mailbox job communication merely to satisfy `peek`.
- Do not treat `peek` as a heartbeat requirement for the master.
- Do not mutate delegation policy, completion condition, or stop posture during ordinary inspection.
- Do not describe `dead` as though it were an operator action.
