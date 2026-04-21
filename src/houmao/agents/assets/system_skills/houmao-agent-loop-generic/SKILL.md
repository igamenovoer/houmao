---
name: houmao-agent-loop-generic
description: Use Houmao's generic loop graph-planning and run-control skill when a user-controlled agent needs to decompose a multi-agent communication graph into pairwise and relay components or operate that run through start, status, and stop.
license: MIT
---

# Houmao Agent Loop Generic

Use this Houmao skill when a user-controlled agent needs to formulate or operate one generic loop graph run across named Houmao agents while keeping the user agent outside the execution loop.

`houmao-agent-loop-generic` is intentionally above the direct-operation skills and above the elemental pairwise and relay pattern pages in `houmao-adv-usage-pattern`. This skill does not invent a new runtime loop engine. It turns user intent into one explicit typed component plan, renders the final generic control graph, and routes start or follow-up control to the maintained Houmao-owned skills that already own messaging, reminders, mailbox follow-up, read-only inspection, and elemental pairwise or relay execution guidance.

The pairwise and relay pages in `houmao-adv-usage-pattern` are atomic protocol pages. This skill owns composed graph planning: mixed pairwise/relay decomposition, multi-edge topology, component dependencies, rendered graphs, graph policy, run charters, and `start`/`status`/`stop` control.

The trigger word `houmao` is intentional. Use the `houmao-agent-loop-generic` skill name directly when you intend to activate this Houmao-owned skill.

## Scope

This packaged skill covers two lanes:

- authoring a generic loop graph plan from user intent
- operating an accepted generic run through `start`, `status`, and `stop`

This packaged skill does not cover:

- making the user agent a participant in pairwise receipts, relay receipts, results, or acknowledgements
- inventing free delegation, free forwarding, or hidden component dependencies when the plan is silent
- drawing arbitrary cyclic worker-to-worker execution as the default model
- replacing `houmao-agent-messaging`, `houmao-agent-gateway`, `houmao-agent-email-comms`, `houmao-agent-inspect`, or `houmao-adv-usage-pattern`
- replacing the explicit pairwise-only planners `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, or `houmao-agent-loop-pairwise-v3` when the user asks for those skills by name

## Workflow

1. Confirm that the user wants one generic loop graph plan or one run-control action rather than one ordinary direct-operation request.
2. Keep the two planes separate from the start:
   - control plane: user agent to designated master or root run owner
   - execution plane: root owner and downstream agents using typed pairwise and relay components
3. Treat the user agent as outside the execution loop. After the root owner accepts the run, that owner owns liveness, supervision, component dispatch, completion evaluation, and stop handling.
4. If the user needs a new plan or a revised plan, load exactly one authoring page:
   - `authoring/formulate-loop-plan.md`
   - `authoring/revise-loop-plan.md`
   - `authoring/render-loop-graph.md`
5. If the user already has a plan and wants to operate it, load exactly one operating page:
   - `operating/start.md`
   - `operating/status.md`
   - `operating/stop.md`
6. Use the local references and templates only when they help normalize the plan or charter:
   - `references/run-charter.md`
   - `references/graph-policy.md`
   - `references/result-routing.md`
   - `references/stop-modes.md`
   - `references/reporting-contract.md`
   - `references/plan-structure.md`
   - `templates/single-file-plan.md`
   - `templates/bundle-plan.md`
7. Route execution to the maintained Houmao-owned skills that own the lower-level surfaces.

## Component Types

- `pairwise`: Use for one immediate driver-worker local-close component. The worker returns the component result to the same driver that sent that component request. Component execution uses the elemental pairwise edge-loop pattern in `houmao-adv-usage-pattern`.
- `relay`: Use for one relay-rooted ordered lane. Ownership moves forward through the lane, and the designated loop egress returns the final component result to the relay origin. Component execution uses the elemental relay-loop pattern in `houmao-adv-usage-pattern`.

## Authoring Pages

- Read [authoring/formulate-loop-plan.md](authoring/formulate-loop-plan.md) when the user has a goal but not yet one valid typed generic loop plan.
- Read [authoring/revise-loop-plan.md](authoring/revise-loop-plan.md) when an existing plan needs to be tightened, restricted, or re-rendered without changing the high-level objective.
- Read [authoring/render-loop-graph.md](authoring/render-loop-graph.md) when the plan needs the final Mermaid graph that shows typed components, component dependencies, result-return paths, where the supervision loop lives, and where completion and stop are evaluated.

## Operating Pages

- Read [operating/start.md](operating/start.md) when the user wants to send one normalized start charter to the designated master or root run owner.
- Read [operating/status.md](operating/status.md) when the user wants a periodic read-only status update from the designated master or root run owner for one `run_id`.
- Read [operating/stop.md](operating/stop.md) when the user wants to stop one active run, with `interrupt-first` as the default stop posture unless graceful stop was requested explicitly.

## References

- Read [references/run-charter.md](references/run-charter.md) for the normalized start charter fields that the user agent sends to the root owner.
- Read [references/graph-policy.md](references/graph-policy.md) to normalize pairwise delegation, relay routing, and component dependency authority explicitly.
- Read [references/result-routing.md](references/result-routing.md) for pairwise local-close result return, relay egress result return, and mixed component result aggregation.
- Read [references/stop-modes.md](references/stop-modes.md) to choose between default interrupt-first stop and explicitly requested graceful stop.
- Read [references/reporting-contract.md](references/reporting-contract.md) for status, completion, and stop-summary expectations across typed components.
- Read [references/plan-structure.md](references/plan-structure.md) for the required single-file versus bundle-plan sections, script inventory fields, and canonical `plan.md` entrypoint rules.

## Templates

- Read [templates/single-file-plan.md](templates/single-file-plan.md) for the compact one-file plan form.
- Read [templates/bundle-plan.md](templates/bundle-plan.md) for the structured directory form with `plan.md` as the canonical entrypoint.

## Routing Guidance

- Route plan delivery, status requests, and stop requests to `houmao-agent-messaging`.
- Route root-owner reminder and live review-loop timing work to `houmao-agent-gateway`.
- Route mailbox receipt, final-result, and acknowledgement semantics referenced by the plan to `houmao-agent-email-comms`.
- Route due downstream read-only peeking and status inspection to `houmao-agent-inspect`.
- Route atomic pairwise component execution semantics to `houmao-adv-usage-pattern`, specifically the elemental pairwise edge-loop pattern.
- Route atomic relay component execution semantics to `houmao-adv-usage-pattern`, specifically the elemental relay-loop pattern.
- Route routine authoring-time structural graph checks and deterministic Mermaid scaffolding to `houmao-mgr internals graph high analyze|slice|render-mermaid` as the first-class helper surface when a NetworkX node-link graph representation is available; keep semantic graph policy, result routing, and final graph review in this skill.
- Do not route normal generic loop planning to `houmao-mgr internals graph low`; keep routine loop-skill graph work on the Houmao-aware `graph high` surface.
- Route specialized pure-pairwise planning to `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, or `houmao-agent-loop-pairwise-v3` only when the user explicitly invokes or has already selected those pairwise-only skills.
- Route project setup, specialist authoring, agent launch, or lifecycle management outside this loop-planning scope to their existing Houmao-owned skills.

## Guardrails

- Do not make the user agent the upstream driver, relay origin, or egress of the execution loop unless the authored plan explicitly does so with a managed user-controlled agent identity.
- Do not allow free delegation or free forwarding unless the plan says so explicitly.
- Do not treat `status` polling as a keepalive signal; the root owner owns liveness after accepting the run.
- Do not default to graceful stop. Default to `interrupt-first` unless the user explicitly requests graceful termination.
- Do not describe the final graph as an arbitrary agent-to-agent cycle when the real execution topology is typed pairwise and relay components plus a supervision loop.
- Do not push composed graph topology, graph policy, rendered graph semantics, or run-control actions down into `houmao-adv-usage-pattern`; those remain in this skill.
- Do not replace the elemental pairwise or relay protocol pages or restate their full mailbox and reminder protocols here; compose them through `houmao-adv-usage-pattern` for each component.
