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
   - scripts, if any
4. If any materially important field is still missing, ask for exactly that missing field instead of improvising it.
5. Break the work into pairwise local-close control edges. The loop is the supervision or review cycle, not an arbitrary worker-to-worker cycle.
6. Normalize delegation policy explicitly using `references/delegation-policy.md`. No free delegation is allowed unless the plan says so explicitly.
7. Draft the plan with `references/plan-structure.md` plus the matching template:
   - `templates/single-file-plan.md`
   - `templates/bundle-plan.md`
8. Render the final graph through `authoring/render-loop-graph.md`.
9. Produce a compact run-charter summary for later `start` delivery through `references/run-charter.md`.

## Authoring Rules

- Treat the user agent as outside the execution loop.
- Treat the designated master as the root run owner after acceptance.
- Use one root `run_id` for the run contract and keep pairwise `edge_loop_id` values as execution-local identifiers owned by the master and workers.
- Preserve delegation restrictions when the user names a limited downstream set.
- Reject or rewrite any execution sketch that depends on child results bypassing the immediate driver.

## Output Checklist

The finalized authored plan should make these items easy to find:

- master
- participants
- delegation policy
- completion condition
- stop mode default
- reporting contract
- script inventory
- Mermaid control graph
