# Start A Generic Loop Graph Run

Use this page when the user already has one authored generic loop graph plan and wants to send one normalized start charter to the designated master or root run owner.

## Workflow

1. Resolve the designated master or root owner and the plan reference:
   - one plan file for the single-file form
   - `plan.md` or the bundle root for the bundle form
2. Confirm that the plan already defines:
   - designated master or root owner
   - participants
   - typed loop components
   - component dependencies
   - graph policy
   - result-routing contract
   - completion condition
   - stop posture
   - reporting contract
3. If any of those control fields is still unclear, return to the authoring lane before sending a start request.
4. Derive or recover the user-visible `run_id`.
5. Build one normalized charter from `references/run-charter.md`.
6. Deliver that charter to the root owner through `houmao-agent-messaging`.
7. Require an explicit root-owner response:
   - `accepted`
   - `rejected`
8. After the root owner accepts the run, the root owner owns liveness, supervision, typed component dispatch, completion evaluation, and stop handling.
9. If the accepted run needs live reminders, mailbox follow-up, or downstream inspection, let the root owner use `houmao-agent-gateway`, `houmao-agent-email-comms`, `houmao-agent-inspect`, and the elemental pairwise or relay patterns in `houmao-adv-usage-pattern`.

## Start Contract

- The user agent is outside the execution loop.
- The start charter is a control-plane message, not the first pairwise request or relay handoff itself.
- The root owner should keep the run alive until the completion condition is satisfied or a stop signal arrives.
- The user agent may poll `status`, but status polling does not keep the run alive.
- The run contract stays distinct from component-local protocol IDs such as `edge_loop_id`, `loop_id`, and `handoff_id`.

## Guardrails

- Do not send the raw user goal alone when the plan has already been normalized.
- Do not ask the user agent to keep the run alive after the root owner accepted it.
- Do not silently widen delegation, forwarding, or component dependency authority while constructing the charter.
- Do not collapse typed component semantics into one ambiguous worker prompt.
