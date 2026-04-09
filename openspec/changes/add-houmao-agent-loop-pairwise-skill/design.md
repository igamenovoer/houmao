## Context

`houmao-adv-usage-pattern` now documents the pairwise edge-loop execution model for local-close driver-worker delegations, but that guidance is written from the perspective of participating managed agents. It does not define the control-plane workflow where an outside user-controlled agent chooses one designated master, formulates a plan over a named set of Houmao agents, and then asks the master to execute and supervise that plan while the user agent remains outside the loop.

The requested skill needs to cover two related but distinct concerns:

- authoring: turn a user's goal into a valid pairwise loop plan with explicit delegation authority, completion conditions, stop semantics, and a rendered control graph,
- operation: send one run charter to the master and let the master own liveness, retries, and downstream pairwise delegations until completion or stop.

The important current constraints are:

- pairwise execution already uses local-close `edge_loop_id` semantics and should not be replaced,
- the user agent is not part of the execution loop and should not be required for loop liveness,
- free delegation is disallowed unless the plan explicitly authorizes it,
- default stop behavior is interrupt-first rather than graceful drain,
- users need the final graph rendered visually, including who controls whom, where the supervision loop lives, and where completion and stop are evaluated,
- the existing runtime primitives are still the ones that do the real work: managed-agent prompts, mailbox follow-up, gateway reminders, and the pairwise edge-loop pattern.

This change is a packaged skill and spec change. It does not add a new workflow engine, scheduler, or runtime API.

## Goals / Non-Goals

**Goals:**

- Define a packaged `houmao-agent-loop-pairwise` system skill for user-controlled pairwise loop planning and operation.
- Separate the authoring lane from the operating lane so that vague user intent can be normalized into a concrete plan before the run starts.
- Define a root run-control contract where the designated master owns liveness after accepting the run.
- Require explicit delegation policy and forbid implicit free delegation.
- Require a Mermaid diagram in the finalized plan that visualizes the control graph, supervision loop, completion condition, and stop condition.
- Define `stop` as interrupt-first by default, with graceful termination only when explicitly requested.

**Non-Goals:**

- Replacing the existing pairwise edge-loop pattern with a new runtime protocol
- Making the user agent a participant in pairwise receipts, results, or acknowledgements
- Defining arbitrary cyclic agent-to-agent execution graphs as a supported default model
- Guaranteeing durable recovery across gateway restart, gateway loss, or managed-agent replacement
- Adding new gateway, mailbox, or manager endpoints

## Decisions

### Provide one new packaged skill with separate authoring and operating lanes

The implementation should add a new packaged system skill named `houmao-agent-loop-pairwise` with local pages for:

- authoring or revising a loop plan,
- rendering the final loop graph,
- operating an accepted plan through `start`, `status`, and `stop`.

Why:

- The authoring problem and the run-control problem are both part of the user-facing workflow, but they are not the same action.
- One skill with two lanes keeps the conceptual model unified without flattening plan writing and run control into one page.

Alternative considered:

- Adding only a runtime control skill and leaving plan authoring as ad hoc freeform prompting. Rejected because the hard correctness requirements here are mostly in the plan normalization step.

### Keep a strict control-plane versus execution-plane split

The design should model two planes explicitly:

- control plane: user agent sends `start`, `status`, and `stop` requests to the master,
- execution plane: the master and downstream workers use the existing pairwise edge-loop pattern for real work.

The user agent remains outside the pairwise loop graph.

Why:

- This matches the user's clarified boundary.
- It prevents the control agent from accidentally becoming a required participant in loop liveness or mailbox acknowledgements.

Alternative considered:

- Treating the user agent as the upstream driver for the root pairwise loop. Rejected because the user explicitly does not want the user agent to keep the loop alive.

### Introduce a root `run_id` distinct from pairwise `edge_loop_id`

The skill should define one root `run_id` for the user-controlled orchestration. The designated master should own that run state separately from the existing per-edge pairwise ledger, while internal delegations continue to use `edge_loop_id` and optional `parent_edge_loop_id`.

Why:

- One run may contain many pairwise edges over time.
- Root run state needs different lifecycle fields than one edge-local delegation round.

Alternative considered:

- Reusing one `edge_loop_id` as the user-visible run identifier. Rejected because that blurs root control state and individual pairwise execution rounds.

### Require explicit delegation policy in the plan

The authoring lane should normalize delegation authority into an explicit policy that the master can enforce. Supported forms should include:

- `delegate_none`
- `delegate_to_named`
- `delegate_freely_within_named_set`
- `delegate_any`

No free delegation is allowed unless the authored plan says so.

Why:

- This is the main safety and control boundary the user asked for.
- It lets the master reject ambiguous plans instead of inventing delegation freedom at runtime.

Alternative considered:

- Allowing the master to improvise downstream delegation when the plan is silent. Rejected because silence here must mean "not authorized," not "probably fine."

### Define the authored execution graph as pairwise local-close topology plus a supervision loop

The authored graph should visualize pairwise execution edges as a tree or DAG of local-close delegations. The "loop" in this skill should refer to the supervisor review cycle, not to arbitrary cyclic worker-to-worker execution edges.

Why:

- The pairwise pattern is local-close by design.
- A graph diagram that literally draws cyclic agent control edges would mislead readers into thinking arbitrary cyclic execution is a supported default.

Alternative considered:

- Encouraging authors to draw the loop as an agent-to-agent cycle. Rejected because it confuses supervision cadence with execution routing.

### Require a Mermaid diagram in every finalized plan

The authoring lane should require a Mermaid fenced diagram in the final plan. That diagram should show:

- the user agent outside the execution loop,
- the designated master,
- the pairwise control edges between immediate drivers and workers,
- the supervision loop owned by the master,
- the completion condition,
- the stop condition and stop propagation posture.

For bundle plans, `plan.md` should include the top-level diagram and may link to additional diagrams in supporting files.

Why:

- The visual graph is part of the requested guidance, not an optional embellishment.
- Mermaid matches the repository's documentation guidance better than ASCII art.

Alternative considered:

- Making the diagram optional or allowing plain-text graph sketches. Rejected because the user asked for a required final graph and repo guidance already prefers Mermaid.

### Support two plan forms with one canonical entrypoint

The authoring lane should support:

- one single-file Markdown plan for smaller runs,
- one bundle directory for larger runs with supporting Markdown files and scripts.

The bundle form should require `plan.md` as the canonical entrypoint and should treat supporting files as explicit references rather than implicit context.

Why:

- Small runs should not require a directory tree.
- Larger runs with scripts and multiple agent notes need more structure than one file.

Alternative considered:

- Requiring only one plan format. Rejected because both simple and structured authoring use cases are clearly in scope.

### Default stop mode to interrupt-first

The operating lane should define `stop` as interrupt-first unless the user explicitly requests graceful termination. The master should stop creating new child loops, interrupt active downstream work, preserve any already-returned partial results, and summarize what was stopped.

Why:

- This matches the requested default operational posture.
- It is easier to explain and less ambiguous than silently attempting graceful drain.

Alternative considered:

- Making graceful drain the default stop behavior. Rejected because the user explicitly wants the opposite default.

### Make status observational and non-liveness-owning

The operating lane should define `status` as periodic read-only observation of the root run. The user agent may poll, but the master must keep the run alive even when no status request arrives.

Why:

- This preserves the clarified ownership split.
- It keeps status from becoming a hidden heartbeat contract.

Alternative considered:

- Using periodic status checks as the loop keepalive. Rejected because that would place liveness back on the user agent.

## Risks / Trade-offs

- [Users may expect arbitrary cyclic execution graphs] → Mitigation: define the authored topology as pairwise local-close edges plus an explicit supervision loop, and reject or rewrite misleading cyclic control graphs.
- [Plan authoring may feel heavy for small runs] → Mitigation: support a single-file plan form and let the authoring lane synthesize structure from natural-language intent.
- [Interrupt-first stop may discard unfinished downstream work] → Mitigation: require the master to preserve returned partial results and summarize interrupted edges.
- [Delegation restrictions may force more up-front clarification] → Mitigation: let the authoring lane normalize clear policy choices instead of leaving delegation ambiguous at runtime.

## Migration Plan

1. Add the new capability spec for `houmao-agent-loop-pairwise-skill`.
2. Add a packaged system skill directory under `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise/`.
3. Implement authoring-lane guidance for single-file plans, bundle plans, delegation policy normalization, and Mermaid graph rendering.
4. Implement operating-lane guidance for `start`, `status`, and `stop` against a designated master.
5. Update system-skill packaging and projection tests to assert that the new skill assets are packaged and routed correctly.

Rollback is low risk: remove the new packaged skill assets, revert the new capability spec, and revert the corresponding packaging tests.

## Open Questions

- None for artifact generation. This design intentionally fixes the default delegation and stop semantics rather than leaving them open.
