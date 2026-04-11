# Formulate A Generic Loop Graph Plan

Use this page when the user has described what they want, but the designated master or root owner still needs one explicit typed loop graph plan rather than a loose natural-language request.

## Workflow

1. Start from the user's goal, constraints, named Houmao agents, and any stated completion or stop conditions.
2. Decide whether the result should be:
   - one single-file Markdown plan for a smaller run
   - one bundle directory with `plan.md` as the canonical entrypoint for a larger run
3. Identify the required control fields before drafting the plan:
   - designated master or root run owner
   - allowed participant set
   - objective
   - typed loop components
   - component dependencies
   - graph policy
   - result-routing contract
   - completion condition
   - stop policy
   - reporting contract
   - scripts, if any
4. If any materially important field is still missing, ask for exactly that missing field instead of improvising it.
5. Decompose the work into typed components:
   - `pairwise` for immediate driver-worker local-close work where the component result returns to the driver
   - `relay` for ordered relay-rooted lanes where ownership moves forward and the egress returns the component result to the relay origin
6. Record each component with `component_id`, `component_type`, participating agents, root/driver/origin, downstream target or lane order, result-return contract, policy, and dependencies.
   - When the topology is represented as NetworkX node-link JSON, treat `houmao-mgr internals graph high` as the first-class structural preflight.
   - Use `houmao-mgr internals graph high analyze --input <graph.json>` to check reachability, leaves, non-leaf participants, cycle posture, branch points, and dependency posture.
   - Use `houmao-mgr internals graph high slice --input <graph.json> --root <agent> --direction descendants` for authoring-time subtree inspection when a component or participant slice is easier to review separately.
7. Normalize graph policy explicitly using `references/graph-policy.md`. No free delegation, free forwarding, or hidden dependency is allowed unless the plan says so explicitly.
8. Draft the plan with `references/plan-structure.md` plus the matching template:
   - `templates/single-file-plan.md`
   - `templates/bundle-plan.md`
9. Render the final graph through `authoring/render-loop-graph.md`.
10. Produce a compact run-charter summary for later `start` delivery through `references/run-charter.md`.

## Authoring Rules

- Treat the user agent as outside the execution loop.
- Treat the designated master or root owner as the run owner after acceptance.
- Use one root `run_id` for the run contract and keep elemental protocol IDs inside their components:
  - `edge_loop_id` values are pairwise component-local identifiers.
  - `loop_id` and `handoff_id` values are relay component-local identifiers.
- Preserve delegation and forwarding restrictions when the user names a limited downstream set.
- Treat `houmao-mgr internals graph high` output as structural evidence only; it does not authorize broader delegation, free forwarding, hidden dependencies, or result-routing changes.
- Keep routine structural graph work on `houmao-mgr internals graph high`; do not use `graph low` primitives for normal typed loop planning.
- Keep pairwise component results anchored to the immediate driver.
- Keep relay component results anchored to the relay origin through the designated egress.
- Reject or rewrite any execution sketch that depends on an arbitrary cyclic worker graph.
- Use the explicit pairwise-only planner instead when the user explicitly invokes `houmao-agent-loop-pairwise` or `houmao-agent-loop-pairwise-v2`.

## Output Checklist

The finalized authored plan should make these items easy to find:

- master or root owner
- participants
- typed loop components
- component dependencies
- graph policy
- result-routing contract
- completion condition
- stop mode default
- reporting contract
- script inventory
- Mermaid generic loop graph
