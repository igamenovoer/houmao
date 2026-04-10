# Normalized Run Charter

Use this reference when the user agent is ready to send one `start` request to the designated master.

## Required Fields

- `run_id`
- `plan_ref`
- designated master identity acting as loop origin
- allowed participants
- route policy summary
- result-return contract summary
- completion condition summary
- default stop mode
- reporting contract summary

## Charter Template

```text
You are the master and loop origin for relay loop run `<run_id>`.

Plan reference:
- type: <single-file | bundle>
- path: <canonical plan path>

Control-plane contract:
- I am outside the execution loop.
- Do not rely on me for liveness.
- Keep this run alive until the completion condition is satisfied or I send stop.
- I may send `status <run_id>` or `stop <run_id>` later.

Execution model:
- Use the Houmao relay-loop pattern for internal routing.
- Each downstream handoff must use the same route policy defined in the plan.
- Each handoff sends a receipt to its immediate upstream sender.
- The loop egress returns the final result to you as loop origin.

Route policy:
<normalized policy from references/route-policy.md>

Result-return contract:
<normalized policy from references/result-contract.md>

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
