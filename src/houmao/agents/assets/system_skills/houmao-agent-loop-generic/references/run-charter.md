# Normalized Run Charter

Use this reference when the user agent is ready to send one `start` request to the designated master or root run owner.

## Required Fields

- `run_id`
- `plan_ref`
- designated master or root owner identity
- allowed participants
- typed component summary
- component dependency summary
- graph policy summary
- result-routing contract summary
- completion condition summary
- default stop mode
- reporting contract summary

## Charter Template

```text
You are the root owner for generic loop graph run `<run_id>`.

Plan reference:
- type: <single-file | bundle>
- path: <canonical plan path>

Control-plane contract:
- I am outside the execution loop.
- Do not rely on me for liveness.
- Keep this run alive until the completion condition is satisfied or I send stop.
- I may send `status <run_id>` or `stop <run_id>` later.

Execution model:
- Use the accepted plan for composed topology, component dependencies, completion, stop, and reporting.
- Use the Houmao elemental pairwise edge-loop pattern for each `pairwise` component.
- Use the Houmao elemental relay-loop pattern for each `relay` component.
- Keep pairwise component results local-close: worker returns to immediate driver.
- Keep relay component results egress-return: loop egress returns to relay origin.

Typed components:
<component_id, component_type, participants, root/driver/origin, downstream targets or lane order>

Graph policy:
<normalized policy from references/graph-policy.md>

Result-routing contract:
<normalized policy from references/result-routing.md>

Completion condition:
<user-defined operational success condition>

Default stop mode:
<interrupt-first | graceful>

Reporting contract:
<status, completion, and stop-summary expectations>

Start procedure:
1. Read the plan.
2. Accept or reject the run explicitly.
3. If accepted, persist root run state, arm supervision, and begin typed component dispatch.
```

## Guardrails

- Keep the charter compact and normalized.
- Send the plan reference and policy summary, not a second unstructured copy of the whole plan.
- Do not omit the statement that the user agent is outside the execution loop.
- Do not collapse typed component semantics into an ambiguous "ask workers until done" instruction.
