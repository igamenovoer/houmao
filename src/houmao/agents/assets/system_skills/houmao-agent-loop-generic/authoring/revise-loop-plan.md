# Revise A Generic Loop Graph Plan

Use this page when a plan already exists, but the user wants to tighten graph boundaries, change the designated master/root owner, revise component dependencies, revise completion or stop policy, add or remove scripts, or re-render the final graph.

## Workflow

1. Read the current canonical plan entrypoint first:
   - the plan file itself for the single-file form
   - `plan.md` first for the bundle form
2. Identify what is changing:
   - objective
   - master or root owner
   - participant set
   - typed components
   - component dependencies
   - graph policy
   - result-routing contract
   - completion condition
   - stop posture
   - reporting contract
   - scripts or plan bundle layout
3. Keep the control-plane versus execution-plane split intact while revising.
4. Preserve the canonical entrypoint:
   - the original plan file for single-file form
   - `plan.md` for bundle form
5. Re-validate every component boundary:
   - `pairwise` components close results back to the immediate driver
   - `relay` components return final results from egress to relay origin
   - component dependencies are explicit
6. Re-validate graph policy. Silence is not authorization for free delegation, free forwarding, or hidden dependencies.
7. When the topology is represented as NetworkX node-link JSON, use `houmao-mgr internals graph high analyze --input <graph.json>` as the structural preflight for reachability, leaves, non-leaf participants, cycle posture, branch points, and dependency posture.
8. Use `houmao-mgr internals graph high slice --input <graph.json> --root <agent> --direction descendants` for focused structural review when a component or participant slice is easier to review separately; treat the slice as structural evidence only.
9. Re-render the Mermaid graph if topology, component type, component dependency, completion, stop posture, or result-routing behavior changed.
10. Refresh the normalized run-charter summary if any user-visible control field changed.

## Revision Guardrails

- Do not quietly widen delegation or forwarding authority while revising another part of the plan.
- Do not convert a pairwise local-close component into a relay component, or the reverse, without making that semantic change explicit.
- Do not leave a stale graph in place after changing the run topology.
- Do not use `graph low` primitives for normal typed loop planning; keep routine structural checks on `houmao-mgr internals graph high`.
- Do not move final completion evaluation away from the designated root owner unless the plan explicitly changes the root owner.
- Do not default a revised stop posture to graceful termination; keep `interrupt-first` unless the user explicitly changed it.
