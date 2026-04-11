# Normalized Run Charter

Use this reference when the user agent is ready to send one `start` request to the designated master.

## Required Fields

- `run_id`
- `plan_ref`
- designated master identity
- allowed participants
- delegation policy summary
- completion condition summary
- default stop mode
- reporting contract summary

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
- I may send `status <run_id>` or `stop <run_id>` later.

Execution model:
- Use the accepted plan for composed topology, recursive child-control edges, completion, stop, and reporting.
- Use the Houmao elemental pairwise edge-loop pattern for each immediate driver-worker delegation edge.
- Every delegation edge must close back to its immediate driver.
- Child results must not bypass the immediate driver.

Delegation policy:
<normalized policy from references/delegation-policy.md>

Completion condition:
<user-defined operational success condition>

Default stop mode:
<interrupt-first | graceful>

Reporting contract:
<status, completion, and stop-summary expectations>

Start procedure:
1. Read the plan.
2. Accept or reject the run explicitly.
3. If accepted, persist root run state, arm supervision, and begin dispatch.
```

## Guardrails

- Keep the charter compact and normalized.
- Send the plan reference and policy summary, not a second unstructured copy of the whole plan.
- Do not omit the statement that the user agent is outside the execution loop.
