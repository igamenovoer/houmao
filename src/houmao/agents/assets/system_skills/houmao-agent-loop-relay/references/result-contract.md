# Result Return Contract

Use this reference when the authored plan or run charter needs to define who acknowledges ownership, who returns the final result, and where that final result lands.

## Immediate Receipt Rules

- Each new downstream handoff sends a receipt to its immediate upstream sender.
- Receipts confirm ownership of the current `handoff_id`; they do not close the whole run.
- Receipts do not replace the final result returned to the origin.

## Final Result Rules

- The designated loop egress returns the final result to the loop origin.
- The loop origin acknowledges the final result back to the loop egress when the pattern requires it.
- The final result target is not left implicit. Record it in the plan and in the run charter summary.

## Guardrails

- Do not confuse per-hop receipt flow with the final-result return path.
- Do not treat an intermediate relay agent as the default final-result target when the plan says the origin closes the run.
- Do not leave loop-egress ownership ambiguous in a multi-hop route.
