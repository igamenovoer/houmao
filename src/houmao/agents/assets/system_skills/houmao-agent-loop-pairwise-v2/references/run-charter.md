# Normalized Run Charter

Use this reference when the user agent is ready to send one `start` request to the designated master.

## Required Fields

- `run_id`
- `plan_ref`
- designated master identity
- allowed participants
- delegation policy summary
- prestart strategy summary
- root routing packet or exact root packet reference
- explicit preparation-wave summary, only when selected
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
- Use the accepted plan for composed topology, recursive child-control edges, completion, stop, reporting, and lifecycle posture.
- Use the Houmao elemental pairwise edge-loop pattern for each immediate driver-worker delegation edge.
- Every delegation edge must close back to its immediate driver.
- Child results must not bypass the immediate driver.

Delegation policy:
<normalized policy from references/delegation-policy.md>

Prestart posture:
- prestart strategy: <precomputed_routing_packets | operator_preparation_wave>
- routing packet validation: <completed | not applicable>
- root routing packet: <inline packet text or exact packet reference>
- child packet forwarding rule: append prepared child packets verbatim to ordinary pairwise edge requests; do not edit, merge, or summarize unless the plan explicitly permits it
- mismatch rule: stop downstream dispatch and report when a child packet is missing, has the wrong recipient, or has a stale plan revision or digest
- operator preparation wave: <not selected | completed>
- acknowledgement mode: <not applicable | fire_and_proceed | require_ack>
- required acknowledgements: <not applicable | completed for targeted preparation recipients>

Completion condition:
<user-defined operational success condition>

Default stop mode:
<interrupt-first | graceful>

Reporting contract:
<peek, completion, and stop-summary expectations using canonical observed states>

Start procedure:
1. Read the plan.
2. Read the root routing packet or exact packet reference.
3. Accept or reject the run explicitly.
4. If accepted, persist root run state, arm supervision, and begin dispatch using the root packet dispatch table.
```

## Guardrails

- Keep the charter compact and normalized.
- Send the plan reference, policy summary, and root routing packet or exact root packet reference, not a second unstructured copy of the whole plan.
- Do not omit the statement that the user agent is outside the execution loop.
- Do not ask the master to infer child packet content from the full plan when the packet inventory should already be authored.
