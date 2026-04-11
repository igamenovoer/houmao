# Graph Policy Forms

Use this reference to normalize pairwise delegation authority, relay forwarding authority, and component dependencies explicitly inside the authored plan and run charter.

## Component Policy Fields

Every component should record:

- `component_id`
- `component_type`
- allowed participant set
- allowed downstream targets or lane order
- delegation or forwarding authority
- result-return target
- dependencies on other components

## Pairwise Delegation Policy

- `delegate_none`
  - No downstream delegation is authorized from this pairwise component.
- `delegate_to_named`
  - Delegation is allowed only to the explicitly named downstream agents listed in the plan.
- `delegate_freely_within_named_set`
  - The acting driver may choose among one explicitly named allowed set without asking again.
- `delegate_any`
  - The acting driver may delegate to any available agent.

## Relay Route Policy

- `fixed_route_only`
  - The relay lane is fully specified and no intermediate variation is authorized.
- `forward_to_named`
  - Forwarding is allowed only to the explicitly named next-hop agents or named sets listed in the plan.
- `forward_freely_within_named_set`
  - The acting upstream owner may choose among one explicitly named allowed set without asking again.
- `forward_any`
  - The acting upstream owner may forward to any available agent.

## Dependency Rules

- List component dependencies explicitly.
- Say whether a component can start only after another component completes, can start after another component sends a receipt, or can run concurrently.
- Do not infer component dependencies from diagram proximity.
- Do not let one component consume hidden upstream-specific context unless the plan names that context and its transfer path.

## Normalization Rules

- Silence is not authorization.
- If the user only names a finite downstream set, keep the policy restricted to that set.
- If the user wants free delegation or free forwarding, encode that explicitly.
- If the user wants multiple relay lanes or multiple pairwise edges, list them as separate components rather than collapsing them into a vague graph.
- Identify which agents may act as relay egresses when a route can branch.

## Guardrails

- Do not widen `delegate_to_named` into `delegate_any`.
- Do not widen `forward_to_named` into `forward_any`.
- Do not infer free delegation or free forwarding authority from the mere existence of multiple participants.
- Do not leave the plan without explicit graph policy for each component.
