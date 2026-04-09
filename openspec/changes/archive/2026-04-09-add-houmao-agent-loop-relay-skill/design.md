## Context

`houmao-adv-usage-pattern` now documents the forward relay-loop execution model for work that moves across one or more downstream agents before a later loop egress returns the final result to the origin. That guidance is written from the perspective of participating managed agents. It does not define the control-plane workflow where an outside user-controlled agent chooses one designated master, formulates a relay plan over a named set of Houmao agents, and then asks that master to execute and supervise that plan while the user agent remains outside the loop.

The requested skill needs to cover two related but distinct concerns:

- authoring: turn a user's goal into a valid relay loop plan with explicit route authority, egress behavior, completion conditions, stop semantics, and a rendered relay graph,
- operation: send one run charter to the designated master and let that master own liveness, retries, and downstream relay handoffs until completion or stop.

The important current constraints are:

- relay execution already uses origin-owned `loop_id` and hop-local `handoff_id` semantics and should not be replaced,
- the user agent is not part of the execution loop and should not be required for loop liveness,
- free downstream forwarding is disallowed unless the plan explicitly authorizes it,
- the designated master should also act as the loop origin so one agent owns run state and final completion,
- default stop behavior is interrupt-first rather than graceful drain,
- users need the final graph rendered visually, including who may hand off to whom, where the supervision loop lives, where the final result returns, and where completion and stop are evaluated,
- the existing runtime primitives are still the ones that do the real work: managed-agent prompts, mailbox follow-up, gateway reminders, and the forward relay-loop pattern.

This change is a packaged skill and spec change. It does not add a new workflow engine, scheduler, or runtime API.

## Goals / Non-Goals

**Goals:**

- Define a packaged `houmao-agent-loop-relay` system skill for user-controlled relay loop planning and operation.
- Separate the authoring lane from the operating lane so that vague user intent can be normalized into a concrete relay plan before the run starts.
- Define a root run-control contract where the designated master, acting as loop origin, owns liveness after accepting the run.
- Require explicit route policy and forbid implicit free forwarding.
- Require a Mermaid diagram in the finalized plan that visualizes the relay graph, supervision loop, completion condition, stop condition, and the final-result return to the origin.
- Define `stop` as interrupt-first by default, with graceful termination only when explicitly requested.

**Non-Goals:**

- Replacing the existing forward relay-loop pattern with a new runtime protocol
- Making the user agent a participant in relay receipts, results, or acknowledgements
- Defining arbitrary cyclic agent-to-agent execution graphs as a supported default model
- Guaranteeing durable recovery across gateway restart, gateway loss, or managed-agent replacement
- Adding new gateway, mailbox, or manager endpoints

## Decisions

### Provide one new packaged skill with separate authoring and operating lanes

The implementation should add a new packaged system skill named `houmao-agent-loop-relay` with local pages for:

- authoring or revising a relay loop plan,
- rendering the final relay graph,
- operating an accepted plan through `start`, `status`, and `stop`.

Why:

- The authoring problem and the run-control problem are both part of the user-facing workflow, but they are not the same action.
- One skill with two lanes keeps the conceptual model unified without flattening plan writing and run control into one page.

Alternative considered:

- Adding only a runtime control skill and leaving relay plan authoring as ad hoc prompting. Rejected because the hard correctness requirements here are mostly in the plan normalization step.

### Keep a strict control-plane versus execution-plane split

The design should model two planes explicitly:

- control plane: user agent sends `start`, `status`, and `stop` requests to the designated master,
- execution plane: the designated master and downstream agents use the existing relay-loop pattern for real work.

The user agent remains outside the relay loop graph.

Why:

- This matches the requested boundary.
- It prevents the control agent from accidentally becoming a required participant in loop liveness, receipts, or final-result acknowledgements.

Alternative considered:

- Treating the user agent as the upstream driver of the first relay hop. Rejected because the user explicitly does not want the user agent to keep the loop alive.

### Make the designated master also be the loop origin

The skill should normalize the designated master and the relay loop origin to the same role for one run.

Why:

- One agent should own the user-visible run state, final completion evaluation, and final result receipt.
- Separating master from origin would introduce unnecessary ambiguity about who owns `run_id`, who receives the final result, and who can declare the run complete.

Alternative considered:

- Allowing one master agent to supervise a distinct origin agent. Rejected because it complicates status and stop semantics without a clear benefit for the packaged workflow.

### Introduce a root `run_id` distinct from relay `loop_id` and `handoff_id`

The skill should define one root `run_id` for the user-controlled orchestration. The designated master or origin should own that run state separately from the per-route relay ledger, while internal relay execution continues to use `loop_id` and hop-local `handoff_id`.

Why:

- One run may contain multiple relay lanes or repeated relay routes over time.
- Root run state needs different lifecycle fields than one relay route or one hop.

Alternative considered:

- Reusing one relay `loop_id` as the user-visible run identifier. Rejected because that blurs root control state and route-local execution state.

### Require explicit route policy in the plan

The authoring lane should normalize downstream forwarding authority into an explicit route policy that the designated master can enforce. Supported forms should include:

- fixed route only,
- forwarding only to named next hops or named sets,
- free forwarding within a named set,
- free forwarding to any agent.

The authored plan should also identify which agents are allowed to act as loop egresses and must preserve the rule that the final result returns to the origin.

Why:

- This is the main safety and control boundary for forward relay work.
- It lets the master reject ambiguous plans instead of inventing forwarding freedom or egress authority at runtime.

Alternative considered:

- Allowing the master or intermediate relay agents to improvise downstream forwarding when the plan is silent. Rejected because silence here must mean "not authorized," not "probably fine."

### Define the authored execution graph as forward relay topology plus a supervision loop

The authored graph should visualize forward handoff edges from the origin through ingress and optional relay agents to one egress, with immediate receipts flowing back one hop and the final result flowing back to the origin. The "loop" in this skill should refer to the supervisor review cycle, not to arbitrary cyclic worker-to-worker execution edges.

Why:

- The forward relay pattern keeps ownership moving downstream until a later egress returns the final result.
- A graph diagram that literally draws cyclic worker control edges would mislead readers into thinking arbitrary cyclic execution is a supported default.

Alternative considered:

- Encouraging authors to draw the loop as a cyclic worker graph. Rejected because it confuses supervision cadence with execution routing.

### Require a Mermaid diagram in every finalized plan

The authoring lane should require a Mermaid fenced diagram in the final plan. That diagram should show:

- the user agent outside the execution loop,
- the designated master as loop origin,
- the relay handoff edges between upstream and downstream agents,
- the immediate receipt path for each handoff,
- the final result return from loop egress to origin,
- the supervision loop owned by the origin,
- the completion condition,
- the stop condition and stop posture.

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
- Larger runs with scripts, route tables, and multiple agent notes need more structure than one file.

Alternative considered:

- Requiring only one plan format. Rejected because both simple and structured authoring use cases are clearly in scope.

### Default stop mode to interrupt-first

The operating lane should define `stop` as interrupt-first unless the user explicitly requests graceful termination. The designated master should stop opening new downstream work, interrupt active downstream relay work, preserve any already-returned partial results, and summarize what was stopped.

Why:

- This matches the requested default operational posture.
- It is easier to explain and less ambiguous than silently attempting graceful drain.

Alternative considered:

- Making graceful drain the default stop behavior. Rejected because the user explicitly wants the opposite default.

### Make status observational and non-liveness-owning

The operating lane should define `status` as periodic read-only observation of the root run. The user agent may poll, but the designated master must keep the run alive even when no status request arrives.

Why:

- This preserves the clarified ownership split.
- It keeps status from becoming a hidden heartbeat contract.

Alternative considered:

- Using periodic status checks as the loop keepalive. Rejected because that would place liveness back on the user agent.

## Risks / Trade-offs

- [Users may expect arbitrary cyclic execution graphs] → Mitigation: define the authored topology as forward relay edges plus an explicit supervision loop, and reject or rewrite misleading cyclic control graphs.
- [Route restrictions may require more up-front clarification] → Mitigation: let the authoring lane normalize clear route-policy choices instead of leaving forwarding ambiguous at runtime.
- [Interrupt-first stop may discard unfinished downstream work] → Mitigation: require the master to preserve returned partial results and summarize interrupted lanes.
- [Relay plans with fan-out can become hard to read] → Mitigation: support a top-level diagram plus supporting route diagrams in bundle plans instead of one overloaded graph.

## Migration Plan

1. Add the new capability spec for `houmao-agent-loop-relay-skill`.
2. Add a packaged system skill directory under `src/houmao/agents/assets/system_skills/houmao-agent-loop-relay/`.
3. Implement authoring-lane guidance for single-file plans, bundle plans, route-policy normalization, result-return rules, and Mermaid graph rendering.
4. Implement operating-lane guidance for `start`, `status`, and `stop` against a designated master or origin.
5. Update system-skill packaging and projection tests to assert that the new skill assets are packaged and routed correctly.

Rollback is low risk: remove the new packaged skill assets, revert the new capability spec, and revert the corresponding packaging tests.

## Open Questions

- None for artifact generation. This design intentionally fixes the default forwarding and stop semantics rather than leaving them open.
