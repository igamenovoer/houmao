# Formulate A Pairwise Loop Plan

Use this page when the user has described a goal, but the designated master still needs one explicit pairwise-v4 plan rather than loose natural-language instructions.

## Inputs

Collect these first:
- user goal and constraints
- source task note path, when the user is planning from a rich task document
- other user-provided source document paths, when they contain schema-like policy verb patterns
- referenced rulebook or commons paths named by the task note or user-provided documents, when available
- named Houmao agents
- completion and stop expectations
- workspace contract expectations
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
   - choose bundle form whenever the run needs reusable reporting or bookkeeping templates under `<plan-output-dir>/templates/`
3. For rich task notes or user-provided documents with schema-like policy verb patterns, perform the v4 source-contract extraction pass before drafting files:
   - read the user task note, user-provided source documents, and available explicitly referenced rulebooks or commons files
   - extract high-salience constraints, hard gates, forbidden actions, state schemas, phase rules, evidence/reporting rules, role-scoped obligations, source-transfer boundaries, and workspace boundaries
   - preserve policy-bearing schema-like verbs when they encode operational policy: `ALWAYS`, `NEVER`, `CHECK`, `RUN`, `READ`, `ANALYZE`, `DECIDE`, `OUTPUT`, `UPDATE`, `COMMIT`, `MERGE`, and `DISPATCH`
   - assign stable source-constraint ids such as `SC-001`
   - distinguish policy-bearing emphasis from decorative emphasis
4. Identify the required control fields:
   - plan output directory
   - canonical entrypoint path: `<plan-output-dir>/plan.md`
   - designated master
   - allowed participant set
   - workspace contract mode: `standard` or `custom`
   - when `standard`, the selected standard posture and any required fields such as `task-name` for in-repo mode
   - when `custom`, the explicit operator-owned launch cwd, source write paths, shared writable paths, bookkeeping paths, read-only paths, and ad hoc worktree posture
   - objective
   - completion condition
   - stop policy
   - reporting contract
   - template inventory, when the run needs reusable reporting or bookkeeping scaffolds
   - lifecycle vocabulary summary
   - authored topology and descendant relationships
   - prestart strategy: `precomputed_routing_packets`
   - optional launch-profile references for participants that `initialize` may launch
   - initialize memo-slot expectations when managed memory is being used
   - continuation page namespace and runtime-owned recovery path family when managed memory is being used
   - exact memo sentinel convention keyed by `run_id` and slot when managed memory is being used
   - gateway mail-notifier interval
   - routing packet inventory
   - optional timeout-watch policy
   - scripts, if any
5. If any materially important field is missing, ask for exactly that field instead of improvising it. When a strict template field is required but the value is intentionally unresolved at authoring time, write `UNRESOLVED - <reason>` in that field.
6. Break the work into pairwise local-close control edges. The loop is the supervision or review cycle, not an arbitrary worker-to-worker cycle.
7. When the topology is represented as NetworkX node-link JSON, use `houmao-mgr internals graph high` as the first-class structural preflight before authoring packets:
   - `houmao-mgr internals graph high analyze --input <graph.json>`
   - `houmao-mgr internals graph high slice --input <graph.json> --root <agent> --direction descendants`
   - `houmao-mgr internals graph high packet-expectations --input <graph.json>`
8. Normalize delegation policy with `references/delegation-policy.md`.
9. Normalize the workspace contract with `references/workspace-contract.md`.
10. Draft the plan with:
   - `references/plan-structure.md`
   - `templates/single-file-plan.md`
   - `templates/bundle-plan.md`
   - `document-templates/plan.md` for rich bundle `plan.md`
   - `document-templates/agent-note.md` for every generated `agents/<participant>.md`
11. Project extracted source constraints:
   - central operator-critical constraints into `plan.md`
   - role-scoped constraints into each relevant `agents/<participant>.md`
   - state schemas into `plan.md` and bookkeeping templates
   - evidence and reporting requirements into `reporting.md`, reporting templates, and role-local gates
   - forbidden actions into central and role-local guardrails for every role that could violate them
   - unresolved constraints into `constraint-coverage-audit.md` with a reason
12. When the run needs reusable report or bookkeeping scaffolds, synthesize a plan-owned template inventory under `<plan-output-dir>/templates/`:
   - derive reporting templates from `references/reporting-contract.md` for the applicable run surfaces such as `peek`, completion, recovery, stop, and `hard-kill`
   - derive bookkeeping templates from the objective, topology, participant roles, and declared bookkeeping paths
   - use `document-templates/reporting-template.md` and `document-templates/bookkeeping-template.md` as strict section contracts
   - keep filenames discoverable through categories such as `templates/reporting/` and `templates/bookkeeping/`
   - keep those template files authored source material rather than mutable runtime artifacts
13. When the plan selects `standard` workspace mode and the operator wants Houmao to prepare or summarize that workspace, route that standard workspace work to the standard workspace-preparation skill. Do not invent a custom lane inside that workspace-preparation path.
14. Author routing packets at plan time:
   - when a node-link graph is available, use `houmao-mgr internals graph high packet-expectations --input <graph.json>` after `analyze` and any needed `slice` calls to derive the root packet, child packet, and non-leaf dispatch-table expectations
   - produce one root packet for the designated master
   - produce one child packet for each parent-to-child pairwise edge
   - include packet id, run id placeholder, plan id and revision or digest, intended recipient, immediate driver, local role and objective, allowed delegation targets, result-return contract, obligations, forbidden actions, and timeout-watch posture when used
   - for every non-leaf recipient, include a child dispatch table and either exact child packet text or exact references to the child packet text that it may forward
   - instruct runtime drivers to append child packets verbatim to pairwise edge request email, without editing, merging, or summarizing them unless the plan explicitly permits that transformation
   - fail closed when a child packet is missing, names a different recipient, or carries a stale plan revision or digest
15. Define the durable initialize and communication posture:
   - default `initialize` validates routing packets and writes run-owned participant memo blocks under exact sentinels
   - default `initialize` checks mailbox association on provided launch profiles, launches missing participants only from profiles that pass that precheck, and otherwise fails closed if required participants remain missing
   - default `initialize` verifies that the designated master and every required participant have email/mailbox support and fails closed when any required participant does not
   - default `initialize` verifies or enables gateway mail-notifier behavior for every required mail-driven participant with supported live gateway and mailbox surfaces
   - ordinary `start` sends the kickoff through mail by default and uses direct prompt delivery only when the user explicitly requests it
   - gateway mail-notifier interval is `5s` unless the user specifies otherwise
   - advise all agents to use the email system for in-loop job communication by default, including pairwise edge requests, receipts, and results
16. Render the final graph through `authoring/render-loop-graph.md`.
17. Produce a master initialize-memo summary plus compact start-trigger summary through `references/run-charter.md`.
18. Write `constraint-coverage-audit.md` with `document-templates/constraint-coverage-audit.md` when the plan was generated from rich task notes, user-provided documents with policy-bearing verb patterns, or referenced rulebooks.
19. Review the coverage audit before reporting completion. Do not claim the generated bundle preserved the source contract when any high-salience rule remains unresolved without an explicit reason.
20. Write the generated plan into the selected output directory.
21. Report the canonical plan path, any generated template inventory, coverage-audit path when present, and the resulting output-directory structure to the user.

## Authoring Rules

- No free delegation is allowed unless the plan says so explicitly.
- Treat the user agent as outside the execution loop.
- Treat the designated master as the root run owner after `start` fires.
- Keep the authored workspace contract explicit and honest.
- For `standard` in-repo posture, treat the task root as `<repo-root>/houmao-ws/<task-name>`.
- For `custom` workspace posture, record explicit paths instead of translating them into Houmao-standard paths.
- When reusable reporting or bookkeeping scaffolds are part of the run contract, use bundle form and keep them under `<plan-output-dir>/templates/`.
- For rich task-note plans or plans derived from user-provided documents with schema-like policy verb patterns, fill the strict document templates instead of inventing new section names or freeform document organization.
- Preserve policy-bearing source verbs when they encode operational rules.
- Keep source-constraint ids stable across `plan.md`, role-local agent notes, templates, and the coverage audit.
- Keep generated template files discoverable and task-shaped rather than forcing one universal filename set.
- Keep authored template files distinct from mutable artifacts written later into declared bookkeeping paths.
- Keep canonical operator actions distinct from observed state names.
- Keep `plan.md` as the canonical plan entrypoint inside the selected output directory for both single-file and bundle forms.
- Use one root `run_id` for the run contract and keep pairwise `edge_loop_id` values as execution-local identifiers owned by the master and workers.
- Preserve delegation restrictions when the user names a limited downstream set.
- Treat `houmao-mgr internals graph high` output as structural evidence only.
- Keep `initialize` separate from the master trigger.
- Keep graph-tool usage before `ready`; runtime recipients use dispatch tables and exact child packets instead of running graph analysis or recomputing descendants.
- Do not require acknowledgement replies before ordinary `start`.
- Do not invent a plan output directory or write plan files outside the selected output directory.
- Do not omit required template fields; fill known values or mark `UNRESOLVED - <reason>`.
- Do not mark the source-constraint coverage audit complete while extracted high-salience constraints have no central, role-local, template, routing, or unresolved audit entry.
- Reject or rewrite any execution sketch that depends on child results bypassing the immediate driver.

## Output Checklist

The finalized authored plan should make these items easy to find:
- output directory
- canonical plan path
- master
- participants
- referenced source task, user-provided document, and rulebook inputs, when used
- source constraints carried forward
- constraint coverage audit, when rich source constraints were extracted
- workspace contract
- authored topology and descendant relationships
- delegation policy
- prestart strategy
- optional launch-profile references
- initialize memo-slot expectations
- continuation page namespace and runtime-owned recovery path family
- memo sentinel convention
- gateway mail-notifier interval
- routing packet inventory and root packet location
- child dispatch tables and packet forwarding guardrails
- in-loop job communication posture
- lifecycle vocabulary
- completion condition
- stop mode default
- reporting contract
- template inventory, when bundle templates are used
- timeout-watch policy, when used
- script inventory
- Mermaid control graph
