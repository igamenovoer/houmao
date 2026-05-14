# Delegation Policy Forms

Use this reference to normalize delegation authority explicitly inside the authored plan and the run charter.

## Supported Policy Forms

- `delegate_none`
  - No downstream delegation is authorized.
- `delegate_to_named`
  - Delegation is allowed only to the explicitly named downstream agents listed in the plan.
- `delegate_freely_within_named_set`
  - The acting driver may choose among one explicitly named allowed set without asking again.
- `delegate_any`
  - The acting driver may delegate to any available agent.

## Normalization Rules

- Silence is not authorization.
- If the user only names a finite downstream set, keep the policy restricted to that set.
- If the user wants free delegation, encode that explicitly.
- If the user wants recursive delegation, say whether that recursion is limited to a named set or not.

## Guardrails

- Do not widen `delegate_to_named` into `delegate_any`.
- Do not infer recursive delegation authority from the mere existence of multiple participants.
- Do not leave the plan without one explicit delegation posture.
