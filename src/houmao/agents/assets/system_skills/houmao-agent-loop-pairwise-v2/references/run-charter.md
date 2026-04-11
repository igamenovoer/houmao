# Normalized Run Charter

Use this reference when the user agent is ready to send one `start` request to the designated master.

## Required Fields

- `run_id`
- `plan_ref`
- designated master identity
- allowed participants
- delegation policy summary
- preparation posture summary
- preparation target summary
- completion condition summary
- default stop mode
- reporting contract summary with canonical observed states

## Charter Template

```text
You are the master for pairwise loop run `<run_id>`.

Plan reference:
- type: <single-file | bundle>
- path: <canonical plan path>

Control-plane contract:
- I am outside the execution loop.
- Do not rely on me for liveness.
- Keep this run alive until the completion condition is satisfied or I send stop.
- I may later ask to `peek master <run_id>`, `pause <run_id>`, `resume <run_id>`, or `stop <run_id>`.

Execution model:
- Use the Houmao pairwise edge-loop pattern for internal delegation.
- Every delegation edge must close back to its immediate driver.
- Child results must not bypass the immediate driver.

Delegation policy:
<normalized policy from references/delegation-policy.md>

Preparation posture:
- notifier preflight: completed
- preparation targets: <delegating_non_leaf | all_participants | named_set>
- targeted preparation wave: completed
- acknowledgement mode: <fire_and_proceed | require_ack>
- required acknowledgements: completed for targeted preparation recipients

Completion condition:
<user-defined operational success condition>

Default stop mode:
<interrupt-first | graceful>

Reporting contract:
<peek, completion, and stop-summary expectations using canonical observed states>

Start procedure:
1. Read the plan.
2. Accept or reject the run explicitly.
3. If accepted, persist root run state, arm supervision, and begin dispatch.
```

## Guardrails

- Keep the charter compact and normalized.
- Send the plan reference and policy summary, not a second unstructured copy of the whole plan.
- Do not omit the statement that the user agent is outside the execution loop.
