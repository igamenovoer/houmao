# Route Policy Forms

Use this reference to normalize forwarding authority explicitly inside the authored plan and the run charter.

## Supported Policy Forms

- `fixed_route_only`
  - The route is fully specified and no intermediate variation is authorized.
- `forward_to_named`
  - Forwarding is allowed only to the explicitly named next-hop agents or named sets listed in the plan.
- `forward_freely_within_named_set`
  - The acting upstream owner may choose among one explicitly named allowed set without asking again.
- `forward_any`
  - The acting upstream owner may forward to any available agent.

## Normalization Rules

- Silence is not authorization.
- If the user only names a finite downstream set, keep the policy restricted to that set.
- If the user wants free forwarding, encode that explicitly.
- If the user wants multiple relay lanes, list them explicitly rather than collapsing them into a vague graph.
- Identify which agents may act as loop egresses when the route can branch.

## Guardrails

- Do not widen `forward_to_named` into `forward_any`.
- Do not infer free forwarding authority from the mere existence of multiple participants.
- Do not leave the plan without one explicit route posture.
