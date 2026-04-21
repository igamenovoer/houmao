# Formulate A Pairwise Loop Plan

Use this page when the user has described a goal, but the designated master still needs one explicit pairwise-v2 plan rather than loose natural-language instructions.

## Inputs

Collect these first:
- user goal and constraints
- named Houmao agents
- completion and stop expectations
- plan output directory

If the plan output directory is not known, ask for it. Do not invent one.

## Output

Write the generated plan under the selected output directory:
- single-file form: `<plan-output-dir>/plan.md`
- bundle form: `<plan-output-dir>/plan.md` plus supporting files under the same directory

## Workflow

1. Resolve the plan output directory before drafting files.
2. Decide the form:
   - single-file plan for a smaller run
   - bundle plan for a larger run
3. Identify the required control fields:
   - plan output directory
   - canonical entrypoint path: `<plan-output-dir>/plan.md`
   - designated master
   - allowed participant set
   - objective
   - completion condition
   - stop policy
   - reporting contract
   - lifecycle vocabulary summary
   - authored topology and descendant relationships
   - prestart strategy: default `precomputed_routing_packets`, or explicit `operator_preparation_wave`
   - durable initialize page namespace and durable start-charter page namespace when managed memory is being used
   - exact memo sentinel convention keyed by `run_id` and slot when managed memory is being used
   - explicit `operator_preparation_wave` target policy
   - gateway mail-notifier interval
   - acknowledgement posture
   - routing packet inventory
   - optional timeout-watch policy
   - scripts, if any
4. If any materially important field is missing, ask for exactly that field instead of improvising it.
5. Break the work into pairwise local-close control edges. The loop is the supervision or review cycle, not an arbitrary worker-to-worker cycle.
6. When the topology is represented as NetworkX node-link JSON, use `houmao-mgr internals graph high` as the first-class structural preflight before authoring packets:
   - `houmao-mgr internals graph high analyze --input <graph.json>`
   - `houmao-mgr internals graph high slice --input <graph.json> --root <agent> --direction descendants`
   - `houmao-mgr internals graph high packet-expectations --input <graph.json>`
7. Normalize delegation policy with `references/delegation-policy.md`.
8. Draft the plan with:
   - `references/plan-structure.md`
   - `templates/single-file-plan.md`
   - `templates/bundle-plan.md`
9. Author routing packets at plan time:
   - when a node-link graph is available, use `houmao-mgr internals graph high packet-expectations --input <graph.json>` after `analyze` and any needed `slice` calls to derive the root packet, child packet, and non-leaf dispatch-table expectations
   - produce one root packet for the designated master
   - produce one child packet for each parent-to-child pairwise edge
   - include packet id, run id placeholder, plan id and revision or digest, intended recipient, immediate driver, local role and objective, allowed delegation targets, result-return contract, obligations, forbidden actions, and timeout-watch posture when used
   - for every non-leaf recipient, include a child dispatch table and either exact child packet text or exact references to the child packet text that it may forward
   - instruct runtime drivers to append child packets verbatim to pairwise edge request email, without editing, merging, or summarizing them unless the plan explicitly permits that transformation
   - fail closed when a child packet is missing, names a different recipient, or carries a stale plan revision or digest
10. Define the durable initialize and communication posture:
   - default `initialize` validates routing packets, writes participant initialize pages, and refreshes exact-sentinel memo reference blocks
   - explicit `operator_preparation_wave` targets delegating or non-leaf participants by default, and adds standalone preparation mail only when selected
   - gateway mail-notifier interval is `5s` unless the user specifies otherwise for `operator_preparation_wave`
   - acknowledgement posture is `fire_and_proceed` unless the user explicitly selects `require_ack`
   - advise all agents to use the email system for in-loop job communication by default, including pairwise edge requests, receipts, and results
11. Render the final graph through `authoring/render-loop-graph.md`.
12. Produce a durable start-charter page summary plus compact start-trigger summary through `references/run-charter.md`.
13. Write the generated plan into the selected output directory.
14. Report the canonical plan path and resulting output-directory structure to the user.

## Authoring Rules

- No free delegation is allowed unless the plan says so explicitly.
- Treat the user agent as outside the execution loop.
- Treat the designated master as the root run owner after acceptance.
- Keep canonical operator actions distinct from observed state names.
- Keep `plan.md` as the canonical plan entrypoint inside the selected output directory for both single-file and bundle forms.
- Use one root `run_id` for the run contract and keep pairwise `edge_loop_id` values as execution-local identifiers owned by the master and workers.
- Preserve delegation restrictions when the user names a limited downstream set.
- Treat `houmao-mgr internals graph high` output as structural evidence only.
- Keep `initialize` separate from the master trigger.
- Keep graph-tool usage before `ready`; runtime recipients use dispatch tables and exact child packets instead of running graph analysis or recomputing descendants.
- Do not require acknowledgement by default; use `fire_and_proceed` unless the user explicitly selects `require_ack`.
- Do not invent a plan output directory or write plan files outside the selected output directory.
- Reject or rewrite any execution sketch that depends on child results bypassing the immediate driver.

## Output Checklist

The finalized authored plan should make these items easy to find:
- output directory
- canonical plan path
- master
- participants
- authored topology and descendant relationships
- delegation policy
- prestart strategy
- durable initialize page namespace
- durable start-charter page namespace
- memo sentinel convention
- explicit `operator_preparation_wave` target policy
- gateway mail-notifier interval
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
