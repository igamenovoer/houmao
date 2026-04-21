---
name: houmao-agent-loop-pairwise-v2
description: Manual invocation only; use only when the user explicitly requests `houmao-agent-loop-pairwise-v2` to author one enriched pairwise loop plan in a user-selected output directory, run routing-packet-first `initialize`, or operate that run through `start`, `peek`, `ping`, `pause`, `resume`, `recover_and_continue`, `stop`, and `hard-kill`.
license: MIT
---

# Houmao Agent Loop Pairwise V2

Use this Houmao skill only when the user explicitly asks for `houmao-agent-loop-pairwise-v2`.

Use this skill only when the user explicitly asks for `houmao-agent-loop-pairwise-v2`.

This is the manual, enriched pairwise-loop skill. It owns:
- pairwise-v2 plan authoring
- prestart preparation
- run-control actions after the plan is accepted

It does not replace the stable `houmao-agent-loop-pairwise` skill, and it is not the default route for generic pairwise-loop requests.

## Quick Use

Use this skill when the user needs one of these:
- `plan`: create or revise an enriched pairwise loop plan
- `initialize`: validate routing packets and prepare durable per-agent run material
- `start`, `peek`, `ping`, `pause`, `resume`, `recover_and_continue`, `stop`, `hard-kill`: operate an accepted run

Do not use this skill for:
- generic pairwise-loop requests when the user did not name `houmao-agent-loop-pairwise-v2`
- making the user agent part of the execution loop
- inventing free delegation when the plan is silent
- replacing `houmao-agent-messaging`, `houmao-agent-gateway`, `houmao-agent-email-comms`, or `houmao-adv-usage-pattern`

## Core Model

- The user agent stays outside the execution loop.
- The designated master owns supervision after `start` is accepted.
- `initialize` is separate from `start`.
- Default prestart strategy is `precomputed_routing_packets`.
- default `precomputed_routing_packets` validates routing packets before the master trigger
- By default, `precomputed_routing_packets` validates routing packets before the master trigger.
- `operator_preparation_wave` is explicit opt-in.
- `resume` is pause-only.
- `recover_and_continue` preserves the same `run_id` after participant stop, kill, or relaunch when the runtime-owned recovery record still marks the run recoverable.
- `hard-kill` is terminal.
- Durable memory work routes through `houmao-memory-mgr`.

## Lifecycle Vocabulary

The canonical operator-facing lifecycle actions are `plan`, `initialize`, `start`, `peek`, `ping`, `pause`, `resume`, `recover_and_continue`, `stop`, and `hard-kill`.

Operator actions:
- `plan`
- `initialize`
- `start`
- `peek`
- `ping`
- `pause`
- `resume`
- `recover_and_continue`
- `stop`
- `hard-kill`

The canonical observed states are `authoring`, `initializing`, `awaiting_ack`, `ready`, `running`, `paused`, `recovering`, `recovered_ready`, `stopping`, `stopped`, and `dead`.

Observed states:
- `authoring`
- `initializing`
- `awaiting_ack`
- `ready`
- `running`
- `paused`
- `recovering`
- `recovered_ready`
- `stopping`
- `stopped`
- `dead`

## Workflow

1. Confirm the user explicitly asked for `houmao-agent-loop-pairwise-v2`.
2. If the request is `plan` and no output directory is known, ask for the output directory before drafting or revising files.
3. Keep the planes separate:
   - control plane: user agent -> designated master
   - execution plane: master -> downstream workers through pairwise edges
4. Choose one lane:
   - authoring: `authoring/formulate-loop-plan.md`, `authoring/revise-loop-plan.md`, `authoring/render-loop-graph.md`
   - prestart: `prestart/prepare-run.md`
   - operations: one page under `operating/`
5. Use references and templates only to normalize the plan or charter.
6. Route lower-level operations to the owning Houmao skills.

## Plan Output Directory

When this skill writes or revises a plan, use one user-selected output directory.

Canonical entrypoint:
- `<plan-output-dir>/plan.md`

Single-file form:

```text
<plan-output-dir>/
  plan.md
```

Bundle form:

```text
<plan-output-dir>/
  plan.md
  prestart.md
  routing-packets.md
  graph.md
  delegation.md
  reporting.md
  scripts/
    README.md
    <script files>
  agents/
    <participant>.md
```

## Pages To Read

Authoring:
- Read [authoring/formulate-loop-plan.md](authoring/formulate-loop-plan.md) when the user has a goal but no valid pairwise-v2 plan yet.
- Read [authoring/revise-loop-plan.md](authoring/revise-loop-plan.md) when an existing plan needs revision.
- Read [authoring/render-loop-graph.md](authoring/render-loop-graph.md) when the plan needs the final Mermaid control graph.

Prestart:
- Read [prestart/prepare-run.md](prestart/prepare-run.md) for `initialize`.

Operations:
- Read [operating/start.md](operating/start.md) for the compact page-backed `start` flow.
- Read [operating/peek.md](operating/peek.md) for read-only inspection.
- Read [operating/ping.md](operating/ping.md) for active messaging to one participant.
- Read [operating/pause.md](operating/pause.md) to suspend wakeup mechanisms.
- Read [operating/resume.md](operating/resume.md) to restore a paused run.
- Read [operating/recover-and-continue.md](operating/recover-and-continue.md) to restore one accepted run after participant stop or relaunch.
- Read [operating/stop.md](operating/stop.md) for canonical stop.
- Read [operating/hard-kill.md](operating/hard-kill.md) for emergency participant-wide interruption and mail draining.

References:
- Read [references/run-charter.md](references/run-charter.md) for the durable start-charter page and compact start trigger.
- Read [references/delegation-policy.md](references/delegation-policy.md) to normalize delegation rules.
- Read [references/stop-modes.md](references/stop-modes.md) to choose stop posture.
- Read [references/reporting-contract.md](references/reporting-contract.md) for `peek`, recovery-summary, completion, stop-summary, and `hard-kill` summary expectations.
- Read [references/plan-structure.md](references/plan-structure.md) for plan layout, required sections, and canonical `plan.md` rules.

Templates:
- Read [templates/single-file-plan.md](templates/single-file-plan.md) for the compact one-file form written as `<plan-output-dir>/plan.md`.
- Read [templates/bundle-plan.md](templates/bundle-plan.md) for the bundle form written under `<plan-output-dir>/`.

## Routing Guidance

Memory and plan material:
- Route any agent memo, `houmao memo`, `houmao-memo.md`, or memo-linked `pages/` request that arises while planning, initializing, or starting a pairwise-v2 run to `houmao-memory-mgr`.
- Route initialize or start managed-memory page and memo reads or writes to `houmao-memory-mgr` and its supported `houmao-mgr agents memory ...` surfaces.

Messaging and mail:
- Route `start`, `ping`, `pause`, `resume`, `recover_and_continue`, `stop`, and participant interrupts within `hard-kill` to `houmao-agent-messaging`.
- Route explicit `operator_preparation_wave` mail-notifier enablement, declarative notifier restoration during `recover_and_continue`, and `hard-kill` notifier shutdown to `houmao-agent-gateway`.
- Route explicit `operator_preparation_wave` preparation mail, in-loop pairwise email traffic, and `hard-kill` mail archiving to `houmao-agent-email-comms`.
- Route operator-mailbox acknowledgement review to `houmao-mailbox-mgr`.

Inspection and structure:
- Route `peek` and overdue downstream inspection to `houmao-agent-inspect`.
- Route authoring-time and initialization structural preflight to `houmao-mgr internals graph high ...`.
- Treat `houmao-mgr internals graph high` output as structural evidence only.

Runtime-owned recovery state:
- Treat `<runtime-root>/loop-runs/pairwise-v2/<run_id>/record.json` plus `events.jsonl` as runtime-owned recovery state for accepted runs; keep that state outside the authored plan bundle and outside participant-local memo or page files.

Execution composition:
- Keep composed topology, recursive child-control edges, rendered graphs, run charters, lifecycle preparation, and run-control actions in this skill.
- Route only the elemental immediate driver-worker edge protocol to `houmao-adv-usage-pattern`.

## Guardrails

Activation:
- Do not auto-route generic pairwise loop planning or pairwise run-control requests here when the user did not explicitly ask for `houmao-agent-loop-pairwise-v2`.
- Do not make the user agent the upstream driver of the execution loop.
- Do not allow free delegation unless the plan says so explicitly.

Plan and memory:
- Do not invent a plan output directory when the user has not provided one; ask for it before writing plan files.
- Do not scatter one authored plan across multiple unrelated directories; keep `plan.md` and supporting files under the selected plan output directory.
- Do not treat live `houmao-memo.md` or memo-linked `pages/` edits as native pairwise-v2 write surfaces; route them to `houmao-memory-mgr`.
- Do not infer memo replacement boundaries from headings, nearby prose, or fuzzy text; use exact `run_id` plus slot sentinels.

Runtime behavior:
- Do not treat standalone participant preparation mail as the default initialize path; it belongs only to explicit `operator_preparation_wave`.
- Do not skip durable initialize pages or exact-sentinel memo reference blocks for participants whose managed memory is being used.
- Do not require intermediate runtime agents to run graph analysis, recompute graph topology, or recompute descendant plan slices.
- Do not edit, merge, or summarize prepared child routing packets during runtime handoff unless the authored plan explicitly permits that transformation.
- Do not repair missing, mismatched, or stale child routing packets by graph reasoning from memory; fail closed and report the mismatch.
- Do not use an interval other than `5s` for explicit `operator_preparation_wave` gateway mail notification unless the user or plan specifies another interval.
- Do not require acknowledgement by default; `require_ack` is explicit and belongs to `operator_preparation_wave`.
- Do not block the current live turn after one downstream dispatch merely because timeout-watch policy exists; use reminder-driven follow-up instead.

Control semantics:
- Do not treat `peek` as a keepalive signal or fresh control prompt.
- Do not treat `ping` as equivalent to `peek`.
- Do not treat `resume` as a synonym for `recover_and_continue`.
- Do not treat `recover_and_continue` as a synonym for `start`.
- Do not default to graceful stop. Default to `interrupt-first` unless the user explicitly requests graceful termination.
- Do not redefine canonical `stop` as an implicit participant-wide broadcast.
- Do not treat `hard-kill` as a synonym for canonical `stop`.
- Do not use ordinary `recover_and_continue` after a terminal `hard-kill`.
- Do not describe `dead` as an operator action.
- Do not describe the final graph as an arbitrary agent-to-agent cycle when the real topology is pairwise local-close control plus a supervision loop.
- Do not leave mail-notifier polling or live reminders active after a `hard-kill`.
- Do not limit `hard-kill` mailbox cleanup to loop-related mail; it intentionally archives every open inbox message for the named participants.
- Do not store mutable recovery ledgers inside the authored plan bundle or inside participant memo pages.
