---
name: houmao-agent-loop-pairwise
description: Use Houmao's manual pairwise loop-planning and run-control skill only when the user explicitly asks for `houmao-agent-loop-pairwise` to formulate a master-owned pairwise loop plan or operate that run through start, status, and stop.
license: MIT
---

# Houmao Agent Loop Pairwise

Use this Houmao skill only when the user explicitly asks for `houmao-agent-loop-pairwise`. This is a manual-invocation-only pairwise loop planner and run controller, not the default entrypoint for generic pairwise loop planning or pairwise run-control requests.

When explicitly invoked, this skill helps a user-controlled agent formulate or operate one pairwise loop run across named Houmao agents while keeping the user agent outside the execution loop.

`houmao-agent-loop-pairwise` is intentionally above the direct-operation skills and above the pairwise pattern page in `houmao-adv-usage-pattern`. This skill does not invent a new runtime loop engine. It turns user intent into one explicit plan, renders the final control graph, and routes start or follow-up control to the maintained Houmao-owned skills that already own messaging, reminders, mailbox follow-up, and pairwise execution guidance.

The trigger word `houmao` is intentional. Use the `houmao-agent-loop-pairwise` skill name directly when you intend to activate this Houmao-owned skill.

## Scope

This packaged skill covers two lanes:

- authoring a pairwise loop plan from user intent
- operating an accepted run through `start`, `status`, and `stop`

This packaged skill does not cover:

- making the user agent a participant in pairwise receipts, results, or acknowledgements
- inventing a free-delegation policy when the plan is silent
- drawing arbitrary cyclic worker-to-worker execution as the default model
- replacing `houmao-agent-messaging`, `houmao-agent-gateway`, `houmao-agent-email-comms`, or `houmao-adv-usage-pattern`

## Workflow

1. Confirm that the user explicitly asked for `houmao-agent-loop-pairwise` and wants one pairwise loop plan or one run-control action rather than one ordinary direct-operation request.
2. Keep the two planes separate from the start:
   - control plane: user agent to designated master
   - execution plane: master and downstream workers using the existing pairwise edge-loop pattern
3. Treat the user agent as outside the execution loop. After the master accepts the run, the master owns liveness, supervision, downstream pairwise dispatch, completion evaluation, and stop handling.
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
   - `references/delegation-policy.md`
   - `references/stop-modes.md`
   - `references/reporting-contract.md`
   - `references/plan-structure.md`
   - `templates/single-file-plan.md`
   - `templates/bundle-plan.md`
7. Route execution to the maintained Houmao-owned skills that own the lower-level surfaces.

## Authoring Pages

- Read [authoring/formulate-loop-plan.md](authoring/formulate-loop-plan.md) when the user has a goal but not yet one valid pairwise loop plan.
- Read [authoring/revise-loop-plan.md](authoring/revise-loop-plan.md) when an existing plan needs to be tightened, restricted, or re-rendered without changing the high-level objective.
- Read [authoring/render-loop-graph.md](authoring/render-loop-graph.md) when the plan needs the final Mermaid control graph that shows who controls whom, where the supervision loop lives, and where completion and stop are evaluated.

## Operating Pages

- Read [operating/start.md](operating/start.md) when the user wants to send one normalized start charter to the designated master.
- Read [operating/status.md](operating/status.md) when the user wants a periodic read-only status update from the designated master for one `run_id`.
- Read [operating/stop.md](operating/stop.md) when the user wants to stop one active run, with `interrupt-first` as the default stop posture unless graceful stop was requested explicitly.

## References

- Read [references/run-charter.md](references/run-charter.md) for the normalized start charter fields that the user agent sends to the master.
- Read [references/delegation-policy.md](references/delegation-policy.md) to normalize delegation authority explicitly instead of leaving it implied.
- Read [references/stop-modes.md](references/stop-modes.md) to choose between default interrupt-first stop and explicitly requested graceful stop.
- Read [references/reporting-contract.md](references/reporting-contract.md) for status, completion, and stop-summary expectations.
- Read [references/plan-structure.md](references/plan-structure.md) for the required single-file versus bundle-plan sections, script inventory fields, and canonical `plan.md` entrypoint rules.

## Templates

- Read [templates/single-file-plan.md](templates/single-file-plan.md) for the compact one-file plan form.
- Read [templates/bundle-plan.md](templates/bundle-plan.md) for the structured directory form with `plan.md` as the canonical entrypoint.

## Routing Guidance

- Route plan delivery, status requests, and stop requests to `houmao-agent-messaging`.
- Route master reminder and live review-loop timing work to `houmao-agent-gateway`.
- Route mailbox receipt, result, or follow-up semantics referenced by the plan to `houmao-agent-email-comms`.
- Route downstream pairwise execution semantics to `houmao-adv-usage-pattern`, specifically the pairwise edge-loop pattern.
- Route project setup, specialist authoring, agent launch, or lifecycle management outside this loop-planning scope to their existing Houmao-owned skills.

## Guardrails

- Do not auto-route generic pairwise loop planning or pairwise run-control requests here when the user did not explicitly ask for `houmao-agent-loop-pairwise`.
- Do not make the user agent the upstream driver of the execution loop.
- Do not allow free delegation unless the plan says so explicitly.
- Do not treat `status` polling as a keepalive signal; the master owns liveness after accepting the run.
- Do not default to graceful stop. Default to `interrupt-first` unless the user explicitly requests graceful termination.
- Do not describe the final graph as an arbitrary agent-to-agent cycle when the real execution topology is pairwise local-close control plus a supervision loop.
- Do not replace the existing pairwise edge-loop pattern or restate its full mailbox and reminder protocol here; compose it through `houmao-adv-usage-pattern`.
