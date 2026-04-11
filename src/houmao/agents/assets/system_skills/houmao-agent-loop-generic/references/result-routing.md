# Result Routing Contract

Use this reference when the authored plan or run charter needs to define who acknowledges ownership, who returns component results, and where final run results land.

## Pairwise Component Rules

- The worker sends the immediate receipt to the driver for the same `edge_loop_id`.
- The worker returns the component final result to the same driver that sent the component request.
- The result does not bypass the immediate driver.
- The driver acknowledges the worker's final result when the elemental pairwise protocol requires it.

## Relay Component Rules

- Each new downstream handoff sends a receipt to its immediate upstream sender.
- Receipts confirm ownership of the current `handoff_id`; they do not close the whole run.
- The designated loop egress returns the component final result to the relay origin.
- The relay origin acknowledges the final result back to the loop egress when the elemental relay protocol requires it.
- The final result target is not left implicit. Record the origin and egress in the plan and in the run charter summary.

## Mixed Graph Rules

- Record how component results aggregate at the root owner.
- Record whether a later component depends on a prior component's receipt, partial output, or final result.
- Keep component-local result routing separate from the root run completion summary.

## Guardrails

- Do not confuse per-hop receipt flow with final-result return.
- Do not treat an intermediate relay agent as the default final-result target when the plan says the origin closes the relay component.
- Do not let a pairwise component result bypass the immediate driver.
- Do not leave component result ownership ambiguous in a mixed graph.
