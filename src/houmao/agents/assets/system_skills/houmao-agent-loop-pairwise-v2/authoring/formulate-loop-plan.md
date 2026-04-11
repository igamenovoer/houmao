# Formulate A Pairwise Loop Plan

Use this page when the user has described what they want, but the designated master still needs one explicit pairwise loop plan rather than a loose natural-language request.

## Workflow

1. Start from the user's goal, constraints, named Houmao agents, and any stated completion or stop conditions.
2. Decide whether the result should be:
   - one single-file Markdown plan for a smaller run
   - one bundle directory with `plan.md` as the canonical entrypoint for a larger run
3. Identify the required control fields before drafting the plan:
   - designated master
   - allowed participant set
   - objective
   - completion condition
   - stop policy
   - reporting contract
   - lifecycle vocabulary summary
   - authored topology and descendant relationships
   - prestart strategy: default `email_initialization`, or explicit packet-only initialization when the user disables email initialization
   - gateway mail-notifier interval: default `5s` unless the user specifies otherwise
   - initialization email target policy: all named participants by default
   - acknowledgement posture: default `fire_and_proceed`, or explicit `require_ack`
   - routing packet inventory, including one root packet for the master and one child packet for each parent-to-child pairwise edge
   - optional timeout-watch policy, when requested
   - scripts, if any
4. If any materially important field is still missing, ask for exactly that missing field instead of improvising it.
5. Break the work into pairwise local-close control edges. The loop is the supervision or review cycle, not an arbitrary worker-to-worker cycle.
   - When the topology is represented as NetworkX node-link JSON, treat `houmao-mgr internals graph high` as the first-class structural preflight before authoring packets.
   - Use `houmao-mgr internals graph high analyze --input <graph.json>` to check root reachability, non-leaf participants, leaves, and child relationships.
   - Use `houmao-mgr internals graph high slice --input <graph.json> --root <agent> --direction descendants` for plan-time descendant or subtree inspection when a participant's downstream packet material is easier to review separately.
6. Normalize delegation policy explicitly using `references/delegation-policy.md`. No free delegation is allowed unless the plan says so explicitly.
7. Draft the plan with `references/plan-structure.md` plus the matching template:
   - `templates/single-file-plan.md`
   - `templates/bundle-plan.md`
8. Author routing packets at plan time:
   - when a node-link graph is available, use `houmao-mgr internals graph high packet-expectations --input <graph.json>` after `analyze` and any needed `slice` calls to derive the root packet, child packet, and non-leaf dispatch-table expectations
   - produce one root packet for the designated master
   - produce one child packet for each parent-to-child pairwise edge in the authored topology
   - include packet id, run id placeholder, plan id and revision or digest, intended recipient, immediate driver, local role and objective, allowed delegation targets, result-return contract, obligations, forbidden actions, and timeout-watch posture when used
   - for every non-leaf recipient, include a child dispatch table and either exact child packet text or exact references to the child packet text that it may forward
   - instruct runtime drivers to append child packets verbatim to pairwise edge request email, without editing, merging, or summarizing them unless the plan explicitly permits that transformation
   - fail closed when a child packet is missing, names a different recipient, or carries a stale plan revision or digest
9. Define the email communication posture:
   - initialization mail targets all named participants by default
   - gateway mail-notifier interval is `5s` unless the user specifies otherwise
   - acknowledgement posture is `fire_and_proceed` unless the user explicitly selects `require_ack`
   - advise all agents to use the email system for in-loop job communication by default, including pairwise edge requests, receipts, and results
10. Render the final graph through `authoring/render-loop-graph.md`.
11. Produce a compact run-charter summary for later `start` delivery through `references/run-charter.md`.

## Authoring Rules

- Treat the user agent as outside the execution loop.
- Treat the designated master as the root run owner after acceptance.
- Keep canonical operator actions distinct from observed state names.
- Use one root `run_id` for the run contract and keep pairwise `edge_loop_id` values as execution-local identifiers owned by the master and workers.
- Preserve delegation restrictions when the user names a limited downstream set.
- Treat `houmao-mgr internals graph high` output as structural evidence only; it does not authorize broader delegation, omit forbidden actions, or replace semantic review of packet content.
- Keep `initialize` separate from the master trigger: default initialization enables gateway email notification first, sends initialization mail with `fire_and_proceed` posture, and validates routing-packet coverage when routing packets are part of the plan.
- Keep graph-tool usage before `ready`; runtime recipients use dispatch tables and exact child packets instead of running graph analysis or recomputing descendants.
- Do not require acknowledgement by default; use `fire_and_proceed` unless the user explicitly selects `require_ack`.
- Reject or rewrite any execution sketch that depends on child results bypassing the immediate driver.

## Output Checklist

The finalized authored plan should make these items easy to find:

- master
- participants
- authored topology and descendant relationships
- delegation policy
- prestart strategy
- gateway mail-notifier interval
- initialization email target policy
- acknowledgement posture
- routing packet inventory and root packet location
- child dispatch tables and packet forwarding guardrails
- in-loop job communication posture
- lifecycle vocabulary
- completion condition
- stop mode default
- reporting contract
- timeout-watch policy, when used
- script inventory
- Mermaid control graph
