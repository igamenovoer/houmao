---
name: houmao-agent-loop-pairwise-v2
description: Manual invocation only; use only when the user explicitly requests `houmao-agent-loop-pairwise-v2` to author one enriched pairwise loop plan, run `initialize`, or operate that run through `start`, `peek`, `ping`, `pause`, `resume`, `stop`, and `hard-kill`.
license: MIT
---

# Houmao Agent Loop Pairwise V2

Use this Houmao skill only when the user explicitly asks for `houmao-agent-loop-pairwise-v2`. This is a manual-invocation-only versioned enriched pairwise authoring, prestart-preparation, and run-control skill, not the restored stable `houmao-agent-loop-pairwise` contract and not the default entrypoint for generic pairwise loop planning or pairwise run-control requests.

When explicitly invoked, this skill helps a user-controlled agent formulate or operate one enriched pairwise loop run across named Houmao agents while keeping the user agent outside the execution loop.

`houmao-agent-loop-pairwise-v2` is intentionally above the direct-operation skills and above the pairwise pattern page in `houmao-adv-usage-pattern`. This skill does not invent a new runtime loop engine. It preserves the enriched pairwise workflow, turns user intent into one explicit plan, renders the final control graph, and routes start or follow-up control to the maintained Houmao-owned skills that already own messaging, reminders, mailbox follow-up, and pairwise execution guidance.

The trigger word `houmao` is intentional. Use the `houmao-agent-loop-pairwise-v2` skill name directly when you intend to activate this Houmao-owned skill.

## Scope

This packaged skill covers three lanes and one canonical operator-facing lifecycle vocabulary:

- `plan`: author or revise a pairwise loop plan from user intent
- `initialize`: complete the targeted prestart wave before the master trigger
- `start`, `peek`, `ping`, `pause`, `resume`, `stop`, and `hard-kill`: operate an accepted run

This packaged skill does not cover:

- making the user agent a participant in pairwise receipts, results, or acknowledgements
- inventing a free-delegation policy when the plan is silent
- drawing arbitrary cyclic worker-to-worker execution as the default model
- replacing `houmao-agent-messaging`, `houmao-agent-gateway`, `houmao-agent-email-comms`, or `houmao-adv-usage-pattern`

## Canonical Lifecycle Actions

The canonical operator-facing lifecycle actions are `plan`, `initialize`, `start`, `peek`, `ping`, `pause`, `resume`, `stop`, and `hard-kill`.

- `plan`: author or revise the pairwise loop contract before the run begins.
- `initialize`: verify participant preparation material, target delegating/non-leaf participants by default, send standalone preparation mail to the targeted recipients, and optionally wait for targeted acknowledgement replies before the master trigger.
- `start`: send the normalized start charter only to the designated master after initialization is complete.
- `peek master|all|<agent-name>`: perform read-only inspection of current run posture without sending a fresh control prompt.
- `ping <agent-name>`: actively message one selected participant to ask what is going on.
- `pause`: suspend the run's wakeup mechanisms so the loop intentionally stalls.
- `resume`: restore the paused wakeup mechanisms for the same run.
- `stop`: send the canonical termination request to the designated master.
- `hard-kill`: directly interrupt every currently known participant, disable mail-notifier polling, remove live reminders, and mark every unread message read even when that mail is unrelated to the run.

If participant-wide advisory stop mail is ever needed, document it separately as `broadcast-stop`; do not treat it as a synonym for canonical `stop`.

## Canonical Observed States

The canonical observed states are `authoring`, `initializing`, `awaiting_ack`, `ready`, `running`, `paused`, `stopping`, `stopped`, and `dead`.

- `authoring`: the plan is still being authored or revised.
- `initializing`: the targeted standalone preparation wave is being prepared or delivered.
- `awaiting_ack`: acknowledgement-gated initialization has sent preparation mail to targeted recipients and is waiting for their required replies.
- `ready`: targeted initialization is complete and the run is ready for `start`.
- `running`: the master accepted the run and owns live supervision.
- `paused`: the run is intentionally stalled because its wakeup mechanisms are suspended.
- `stopping`: a stop request is being reconciled by the master.
- `stopped`: the run has completed stop handling.
- `dead`: an observed liveness failure or no-progress condition, not a control action.

## Workflow

1. Confirm that the user explicitly asked for `houmao-agent-loop-pairwise-v2` and wants one pairwise loop plan or one run-control action rather than one ordinary direct-operation request.
2. Keep the two planes separate from the start:
   - control plane: user agent to designated master
   - execution plane: master and downstream workers using the existing pairwise edge-loop pattern
3. Treat the user agent as outside the execution loop. After the master accepts the run, the master owns liveness, supervision, downstream pairwise dispatch, completion evaluation, and stop handling.
4. If the user needs a new plan or a revised plan, load exactly one authoring page:
   - `authoring/formulate-loop-plan.md`
   - `authoring/revise-loop-plan.md`
   - `authoring/render-loop-graph.md`
5. If the user needs the preparation wave, load:
   - `prestart/prepare-run.md`
6. If the user already has a plan and wants to operate it, load exactly one operating page:
   - `operating/start.md`
   - `operating/peek.md`
   - `operating/ping.md`
   - `operating/pause.md`
   - `operating/resume.md`
   - `operating/stop.md`
   - `operating/hard-kill.md`
7. Use the local references and templates only when they help normalize the plan or charter:
   - `references/run-charter.md`
   - `references/delegation-policy.md`
   - `references/stop-modes.md`
   - `references/reporting-contract.md`
   - `references/plan-structure.md`
   - `templates/single-file-plan.md`
   - `templates/bundle-plan.md`
8. Route execution to the maintained Houmao-owned skills that own the lower-level surfaces.

## Authoring Pages

- Read [authoring/formulate-loop-plan.md](authoring/formulate-loop-plan.md) when the user has a goal but not yet one valid pairwise loop plan.
- Read [authoring/revise-loop-plan.md](authoring/revise-loop-plan.md) when an existing plan needs to be tightened, restricted, or re-rendered without changing the high-level objective.
- Read [authoring/render-loop-graph.md](authoring/render-loop-graph.md) when the plan needs the final Mermaid control graph that shows who controls whom, where the supervision loop lives, and where completion and stop are evaluated.

## Operating Pages

- Read [operating/start.md](operating/start.md) when the user wants to send one normalized start charter to the designated master.
- Read [operating/peek.md](operating/peek.md) when the user wants `peek master`, `peek all`, or `peek <agent-name>` as read-only inspection of one known run.
- Read [operating/ping.md](operating/ping.md) when the user wants to actively ask one selected participant what is going on.
- Read [operating/pause.md](operating/pause.md) when the user wants to intentionally stall one running pairwise loop by suspending its wakeup mechanisms.
- Read [operating/resume.md](operating/resume.md) when the user wants to restore one paused pairwise loop without creating a new run.
- Read [operating/stop.md](operating/stop.md) when the user wants to stop one active run, with `interrupt-first` as the default stop posture unless graceful stop was requested explicitly.
- Read [operating/hard-kill.md](operating/hard-kill.md) when the user wants emergency participant-wide interruption plus reminder or notifier shutdown and mailbox unread draining for one accepted run.

## Prestart Page

- Read [prestart/prepare-run.md](prestart/prepare-run.md) when the user wants to verify notifier posture, send standalone preparation mail to delegating/non-leaf participants by default, explicitly include leaf participants, or require targeted readiness acknowledgement replies before the master trigger.

## References

- Read [references/run-charter.md](references/run-charter.md) for the normalized start charter fields that the user agent sends to the master.
- Read [references/delegation-policy.md](references/delegation-policy.md) to normalize delegation authority explicitly instead of leaving it implied.
- Read [references/stop-modes.md](references/stop-modes.md) to choose between default interrupt-first stop and explicitly requested graceful stop.
- Read [references/reporting-contract.md](references/reporting-contract.md) for `peek`, completion, stop-summary, and `hard-kill` summary expectations plus the canonical observed-state vocabulary.
- Read [references/plan-structure.md](references/plan-structure.md) for the required single-file versus bundle-plan sections, lifecycle vocabulary fields, script inventory fields, and canonical `plan.md` entrypoint rules.

## Templates

- Read [templates/single-file-plan.md](templates/single-file-plan.md) for the compact one-file plan form.
- Read [templates/bundle-plan.md](templates/bundle-plan.md) for the structured directory form with `plan.md` as the canonical entrypoint.

## Routing Guidance

- Route `start`, `ping`, `pause`, `resume`, `stop`, and participant interrupts within `hard-kill` requests to `houmao-agent-messaging`.
- Route `initialize` notifier preflight and wakeup-control work plus `hard-kill` reminder or mail-notifier shutdown to `houmao-agent-gateway`.
- Route mailbox receipt, result, or follow-up semantics referenced by the plan plus `hard-kill` unread draining to `houmao-agent-email-comms`.
- Route operator-mailbox acknowledgement review to `houmao-mailbox-mgr` or the owned mailbox surfaces that expose `HOUMAO-operator@houmao.localhost`.
- Route `peek` requests, overdue downstream peeking, and other read-only state inspection to `houmao-agent-inspect`.
- Route downstream pairwise execution semantics to `houmao-adv-usage-pattern`, specifically the pairwise edge-loop pattern.
- Route project setup, specialist authoring, agent launch, or lifecycle management outside this loop-planning scope to their existing Houmao-owned skills.

## Guardrails

- Do not auto-route generic pairwise loop planning or pairwise run-control requests here when the user did not explicitly ask for `houmao-agent-loop-pairwise-v2`.
- Do not make the user agent the upstream driver of the execution loop.
- Do not allow free delegation unless the plan says so explicitly.
- Do not treat `peek` as a keepalive signal or fresh control prompt; the master owns liveness after accepting the run.
- Do not treat `ping` as equivalent to `peek`.
- Do not default to graceful stop. Default to `interrupt-first` unless the user explicitly requests graceful termination.
- Do not redefine canonical `stop` as an implicit participant-wide broadcast; keep any advisory `broadcast-stop` action separate.
- Do not treat `hard-kill` as a synonym for canonical `stop`; `hard-kill` is the explicit participant-wide emergency override.
- Do not assume that one participant preparation brief may depend on hidden upstream-specific context from another brief.
- Do not send preparation mail to leaf participants by default; include leaf participants only when the user explicitly asks to prepare leaf agents, prepare all participants, or names leaf participants in the preparation target set.
- Do not block the current live turn after one downstream dispatch merely because timeout-watch policy exists; use reminder-driven follow-up instead.
- Do not describe `dead` as an operator action.
- Do not describe the final graph as an arbitrary agent-to-agent cycle when the real execution topology is pairwise local-close control plus a supervision loop.
- Do not replace the existing pairwise edge-loop pattern or restate its full mailbox and reminder protocol here; compose it through `houmao-adv-usage-pattern`.
- Do not leave mail-notifier polling or live reminders active after a `hard-kill`.
- Do not limit `hard-kill` mailbox cleanup to loop-related mail; it intentionally marks every unread message read for the named participants.
