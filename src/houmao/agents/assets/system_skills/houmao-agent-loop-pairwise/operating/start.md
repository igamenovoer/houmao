# Start A Pairwise Loop Run

Use this page when the user already has one authored plan and wants to send one normalized start charter to the designated master.

## Workflow

1. Resolve the designated master and the plan reference:
   - one plan file for the single-file form
   - `plan.md` or the bundle root for the bundle form
2. Confirm that the plan already defines:
   - designated master
   - participants
   - delegation policy
   - completion condition
   - stop posture
   - reporting contract
3. If any of those control fields is still unclear, return to the authoring lane before sending a start request.
4. Derive or recover the user-visible `run_id`.
5. For every targeted participant with a live gateway and mailbox binding, enable gateway mail-notifier polling through `houmao-agent-gateway` before delivering the start charter. Use interval `5s` unless the user or plan specifies another interval. Skip this step only when the user explicitly disables notifier setup or the participant has no supported live gateway or mailbox binding.
6. Build one normalized charter from `references/run-charter.md`.
7. Deliver that charter to the master through `houmao-agent-messaging`.
8. Require an explicit master response:
   - `accepted`
   - `rejected`
9. After the master accepts the run, the master owns liveness, supervision, downstream pairwise dispatch, completion evaluation, and stop handling.
10. If the accepted run needs live reminders or mailbox follow-up, let the master use `houmao-agent-gateway`, `houmao-agent-email-comms`, and the elemental pairwise pattern in `houmao-adv-usage-pattern` for each immediate driver-worker edge while keeping composed run topology in the accepted plan.

## Start Contract

- The user agent is outside the pairwise execution loop.
- The start charter is a control-plane message, not a root pairwise execution edge.
- The master should keep the run alive until the completion condition is satisfied or a stop signal arrives.
- The user agent may poll `status`, but status polling does not keep the run alive.

## Guardrails

- Do not send the raw user goal alone when the plan has already been normalized.
- Do not ask the user agent to keep the run alive after the master accepted it.
- Do not silently widen delegation authority while constructing the charter.
- Do not skip gateway mail-notifier enablement before delivering the start charter when targeted participants have a live gateway and mailbox binding, unless the user explicitly disables notifier setup.
- Do not use a mail-notifier interval other than `5s` unless the user or plan specifies another interval.
