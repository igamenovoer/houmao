---
name: houmao-agent-loop-pairwise-v4
description: Manual invocation only; use only when the user explicitly requests `houmao-agent-loop-pairwise-v4` to author one template-driven workspace-aware enriched tree loop plan in a user-selected output directory, preserve source constraints from rich task notes or user-provided documents through strict generated document templates and a coverage audit, run routing-packet-validated memo-first `initialize`, or operate that run through `start`, `peek`, `ping`, `pause`, `resume`, `recover_and_continue`, `stop`, and `hard-kill`.
license: MIT
---

# Houmao Agent Loop Tree V4

## Terminology

- This pairwise-named package authors and operates template-driven workspace-aware enriched tree loops.
- `pairwise loop` is a legacy alias for tree loop behavior.
- Keep the package name, explicit invocation name, filenames, and existing runtime identifiers unchanged.
- The elemental driver-worker protocol is a local-close edge loop.

Use this Houmao skill only when the user explicitly asks for `houmao-agent-loop-pairwise-v4`.

This is the manual, template-driven workspace-aware enriched tree loop skill. It owns:
- pairwise-v4 plan authoring
- authored workspace-contract choice
- strict generated document templates
- source-constraint extraction, projection, and coverage audit
- prestart preparation
- run-control actions after the plan is prepared

It extends `houmao-agent-loop-pairwise-v3` instead of replacing the stable `houmao-agent-loop-pairwise` skill or mutating v3 in place.

## Quick Use

Use this skill when the user needs one of these:
- `plan`: create or revise a template-driven workspace-aware enriched tree loop plan
- `initialize`: validate routing packets, verify baseline mail wakeup posture, and write durable per-agent memo guidance
- `start`, `peek`, `ping`, `pause`, `resume`, `recover_and_continue`, `stop`, `hard-kill`: operate a prepared or active run

Do not use this skill for:
- ordinary tree-loop requests when the user did not name `houmao-agent-loop-pairwise-v4`
- making the user agent part of the execution loop
- inventing free delegation when the plan is silent
- translating a custom operator workspace into a Houmao-standard workspace behind the user's back
- replacing `houmao-agent-messaging`, `houmao-agent-gateway`, `houmao-agent-email-comms`, `houmao-agent-inspect`, the standard workspace-preparation skill, or `houmao-adv-usage-pattern`

## Core Model

- The user agent stays outside the execution loop.
- The designated master owns supervision after `start` fires.
- `initialize` is separate from `start`.
- Default prestart strategy is `precomputed_routing_packets`.
- By default, `precomputed_routing_packets` validates routing packets before the master trigger and then materializes per-agent memo guidance directly.
- When the plan provides launch profiles for missing participants, `initialize` first checks mailbox association on those profiles, then may launch them before mail-capability checks and memo materialization continue.
- This package requires email/mailbox support for the designated master and every required participant; if any required participant lacks it, `initialize` and `recover_and_continue` fail closed.
- `initialize` verifies or enables gateway mail-notifier behavior for every required mail-driven participant with supported live gateway and mailbox surfaces.
- `resume` is pause-only.
- `recover_and_continue` preserves the same `run_id` after participant stop, kill, or relaunch when the runtime-owned recovery record still marks the run recoverable.
- `hard-kill` is terminal.
- Every authored plan records a `workspace_contract` with mode `standard` or `custom`.
- `standard` workspace mode uses Houmao's standard workspace posture and may rely on the standard workspace-preparation skill.
- `custom` workspace mode records explicit operator-owned paths directly in the plan and does not route through that standard workspace-preparation lane.
- Standard in-repo posture is task-scoped under `<repo-root>/houmao-ws/<task-name>/...`.
- Durable memory work routes through `houmao-memory-mgr`.
- Runtime-owned recovery state stays under `<runtime-root>/loop-runs/pairwise-v2/<run_id>/...` and remains outside the authored workspace contract.
- Template-driven planning is template-first: the planner fills strict document sections and required fields instead of freeform-organizing rich task contracts.
- Template-driven planning extracts policy-bearing source constraints from the user task, referenced rulebooks, and user-provided documents that use schema-like policy verb patterns, then projects them into central plan, role-local agent notes, reporting/bookkeeping templates, routing surfaces, or an explicit unresolved entry.
- Policy-bearing verbs such as `ALWAYS`, `NEVER`, `CHECK`, `RUN`, `READ`, `ANALYZE`, `DECIDE`, `OUTPUT`, `UPDATE`, `COMMIT`, `MERGE`, and `DISPATCH` remain visible when they encode operational policy.
- Rich bundle plans include a constraint coverage audit that maps source rules to generated bundle locations.

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

The canonical observed states are `authoring`, `initializing`, `ready`, `running`, `paused`, `recovering`, `recovered_ready`, `stopping`, `stopped`, and `dead`.

Observed states:
- `authoring`
- `initializing`
- `ready`
- `running`
- `paused`
- `recovering`
- `recovered_ready`
- `stopping`
- `stopped`
- `dead`

## Workflow

1. Confirm the user explicitly asked for `houmao-agent-loop-pairwise-v4`.
2. If the request is `plan` and no output directory is known, ask with `Required: plan output directory` and an `Optional` section for plan form, workspace hints, template/source-document hints, naming preference, or `none for this step` before drafting or revising files.
3. Keep the planes separate:
   - control plane: user agent -> designated master
   - execution plane: master -> downstream workers through local-close edges
4. Choose one lane:
   - authoring: `authoring/formulate-loop-plan.md`, `authoring/revise-loop-plan.md`, `authoring/render-loop-graph.md`
   - prestart: `prestart/prepare-run.md`
   - operations: one page under `operating/`
5. For `plan`, run the v4 source-contract workflow before writing files:
   - extract high-salience source constraints from the user task, available referenced rulebooks, and user-provided documents with schema-like policy verb patterns
   - project each constraint into central, role-local, reporting, bookkeeping, routing, or unresolved audit surfaces
   - fill strict generated document templates from `document-templates/`
   - review the coverage audit before reporting the bundle complete
6. Use references and templates to normalize the plan, workspace contract, or charter, and when the run needs reusable reporting or bookkeeping scaffolds, synthesize a plan-owned template bundle under the selected output directory.
7. Route lower-level operations to the owning Houmao skills.

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
  workspace-contract.md
  prestart.md
  routing-packets.md
  graph.md
  delegation.md
  reporting.md
  constraint-coverage-audit.md
  templates/
    README.md
    reporting/
      <report-template>.md
    bookkeeping/
      <task-shaped-template>.md
  scripts/
    README.md
    <script files>
  agents/
    <participant>.md
```

## Pages To Read

Authoring:
- Read [authoring/formulate-loop-plan.md](authoring/formulate-loop-plan.md) when the user has a goal but no valid pairwise-v4 plan yet.
- Read [authoring/revise-loop-plan.md](authoring/revise-loop-plan.md) when an existing plan needs revision.
- Read [authoring/render-loop-graph.md](authoring/render-loop-graph.md) when the plan needs the final Mermaid control graph.

Prestart:
- Read [prestart/prepare-run.md](prestart/prepare-run.md) for `initialize`.

Operations:
- Read [operating/start.md](operating/start.md) for the compact mail-first memo-read `start` flow.
- Read [operating/peek.md](operating/peek.md) for read-only inspection.
- Read [operating/ping.md](operating/ping.md) for active messaging to one participant.
- Read [operating/pause.md](operating/pause.md) to suspend wakeup mechanisms.
- Read [operating/resume.md](operating/resume.md) to restore a paused run.
- Read [operating/recover-and-continue.md](operating/recover-and-continue.md) to restore one started run after participant stop or relaunch.
- Read [operating/stop.md](operating/stop.md) for canonical stop.
- Read [operating/hard-kill.md](operating/hard-kill.md) for emergency participant-wide interruption and mail draining.

References:
- Read [references/workspace-contract.md](references/workspace-contract.md) to normalize `standard` versus `custom` workspace contracts.
- Read [references/run-charter.md](references/run-charter.md) for the master memo contract, compact start trigger, and recovery continuation material.
- Read [references/delegation-policy.md](references/delegation-policy.md) to normalize delegation rules.
- Read [references/stop-modes.md](references/stop-modes.md) to choose stop posture.
- Read [references/reporting-contract.md](references/reporting-contract.md) for `peek`, recovery-summary, completion, stop-summary, and `hard-kill` summary expectations.
- Read [references/plan-structure.md](references/plan-structure.md) for plan layout, required sections, and canonical `plan.md` rules.

Templates:
- Read [templates/single-file-plan.md](templates/single-file-plan.md) for the compact one-file form written as `<plan-output-dir>/plan.md`.
- Read [templates/bundle-plan.md](templates/bundle-plan.md) for the bundle form written under `<plan-output-dir>/`, including plan-owned reporting and bookkeeping templates when the run needs reusable scaffolds.

Strict generated document templates:
- Read [document-templates/plan.md](document-templates/plan.md) before generating canonical `plan.md` for a rich bundle.
- Read [document-templates/agent-note.md](document-templates/agent-note.md) before generating any `agents/<participant>.md` note.
- Read [document-templates/reporting-template.md](document-templates/reporting-template.md) before generating reusable reporting templates.
- Read [document-templates/bookkeeping-template.md](document-templates/bookkeeping-template.md) before generating reusable bookkeeping templates.
- Read [document-templates/constraint-coverage-audit.md](document-templates/constraint-coverage-audit.md) before finalizing rich bundle plans from task notes, referenced rulebooks, or user-provided documents with policy-bearing verb patterns.

## Routing Guidance

Memory and plan material:
- Route any agent memo, `houmao memo`, `houmao-memo.md`, or memo-linked `pages/` request that arises while planning, initializing, or starting a pairwise-v4 run to `houmao-memory-mgr`.
- Route initialize memo writes, recovery-page writes, and related managed-memory reads or writes to `houmao-memory-mgr` and its supported `houmao-mgr agents memory ...` surfaces.

Participant launch:
- When a pairwise-v4 plan provides launch-profile-backed birth-time references for missing participants, route those launches through `houmao-agent-instance`.

Workspace posture:
- Route standard workspace preparation or standard workspace summaries to the standard workspace-preparation skill.
- Keep that workspace-preparation lane standard-only. Do not route custom operator-owned layouts through it as if it were a custom-workspace inspector.

Messaging and mail:
- Route ordinary `start` to `houmao-agent-email-comms` by default, and use `houmao-agent-messaging` only when the user explicitly asks for direct prompt delivery.
- Route `ping`, `pause`, `resume`, `recover_and_continue`, `stop`, and participant interrupts within `hard-kill` to `houmao-agent-messaging`.
- Route baseline initialize mail-notifier setup, agent email-notification re-enable work during `recover_and_continue`, declarative notifier restoration, and `hard-kill` notifier shutdown to `houmao-agent-gateway`.
- Route in-loop local-close email traffic and `hard-kill` mail archiving to `houmao-agent-email-comms`.

Inspection and structure:
- Route `peek` and overdue downstream inspection to `houmao-agent-inspect`.
- Route authoring-time and initialization structural preflight to `houmao-mgr internals graph high ...`.
- Treat `houmao-mgr internals graph high` output as structural evidence only.

Runtime-owned recovery state:
- Treat `<runtime-root>/loop-runs/pairwise-v2/<run_id>/record.json` plus `events.jsonl` as runtime-owned recovery state for started runs; keep that state outside the authored plan bundle, outside participant-local memo or page files, and outside the authored workspace contract.

Execution composition:
- Keep composed topology, recursive child-control edges, rendered graphs, workspace contracts, run charters, lifecycle preparation, and run-control actions in this skill.
- Route only the elemental immediate driver-worker edge protocol to `houmao-adv-usage-pattern`.

## Guardrails

Activation:
- Do not auto-route ordinary tree loop planning or tree loop run-control requests here when the user did not explicitly ask for `houmao-agent-loop-pairwise-v4`.
- Do not make the user agent the upstream driver of the execution loop.
- Do not allow free delegation unless the plan says so explicitly.

Plan, workspace, and memory:
- Do not invent a plan output directory when the user has not provided one; ask with separate `Required` and `Optional` values before writing plan files.
- Do not scatter one authored plan across multiple unrelated directories; keep `plan.md` and supporting files under the selected plan output directory.
- Do not omit the authored workspace contract from the v4 plan.
- Do not silently translate a custom workspace contract into `houmao-ws/...`.
- Do not freeform-organize a rich v4 bundle when a strict generated document template exists for that surface.
- Do not delete required template fields; fill known values or write `UNRESOLVED - <reason>`.
- Do not flatten policy-bearing source verbs such as `ALWAYS`, `NEVER`, `CHECK`, `RUN`, `READ`, `ANALYZE`, `DECIDE`, `OUTPUT`, `UPDATE`, `COMMIT`, `MERGE`, or `DISPATCH` into vague prose.
- Do not claim source-contract preservation until the constraint coverage audit maps extracted high-salience rules to generated central and runtime surfaces.
- Do not leave a run in single-file form when its reporting contract or bookkeeping posture clearly needs reusable plan-owned templates; switch that run to bundle form.
- Do not treat files under `<plan-output-dir>/templates/` as live runtime state; they are authored reusable source artifacts for the run.
- Do not prescribe a fixed subtree under per-agent `kb/`; custom bookkeeping paths are task-specific and must be declared explicitly.
- Do not treat live `houmao-memo.md` or memo-linked `pages/` edits as native pairwise-v4 write surfaces; route them to `houmao-memory-mgr`.
- Do not infer memo replacement boundaries from headings, nearby prose, or fuzzy text; use exact `run_id` plus slot sentinels.

Runtime behavior:
- Do not send standalone participant preparation mail during pairwise-v4 `initialize`.
- Do not treat gateway mail-notifier setup as optional for required mail-driven participants with supported live gateway and mailbox surfaces.
- Do not invent launch profiles for missing participants during `initialize`.
- Do not skip run-owned initialize memo materialization or exact-sentinel memo blocks for participants whose managed memory is being used.
- Do not proceed with pairwise-v4 when any required participant lacks email/mailbox support.
- Do not default ordinary `start` to direct prompt delivery; use mail unless the user explicitly asks otherwise.
- Do not require intermediate runtime agents to run graph analysis, recompute graph topology, or recompute descendant plan slices.
- Do not edit, merge, or summarize prepared child routing packets during runtime handoff unless the authored plan explicitly permits that transformation.
- Do not repair missing, mismatched, or stale child routing packets by graph reasoning from memory; fail closed and report the mismatch.
- Do not require acknowledgement replies before ordinary `start`.
- Do not block the current live turn after one downstream dispatch merely because timeout-watch policy exists; use reminder-driven follow-up instead.
- Do not redefine runtime-owned recovery files as ordinary workspace or bookkeeping artifacts.

Control semantics:
- Do not treat `peek` as a keepalive signal or fresh control prompt.
- Do not treat `ping` as equivalent to `peek`.
- Do not treat `resume` as a synonym for `recover_and_continue`.
- Do not treat `recover_and_continue` as a synonym for `start`.
- Do not wait for ordinary `start` to return `accepted` or `rejected`; that handshake belongs only to `recover_and_continue`.
- Do not default to graceful stop. Default to `interrupt-first` unless the user explicitly requests graceful termination.
- Do not redefine canonical `stop` as an implicit participant-wide broadcast.
- Do not treat `hard-kill` as a synonym for canonical `stop`.
- Do not use ordinary `recover_and_continue` after a terminal `hard-kill`.
- Do not describe `dead` as an operator action.
- Do not describe the final graph as an arbitrary agent-to-agent cycle when the real topology is tree loop local-close control plus a supervision loop.
- Do not leave mail-notifier polling or live reminders active after a `hard-kill`.
- Do not limit `hard-kill` mailbox cleanup to loop-related mail; it intentionally archives every open inbox message for the named participants.
- Do not store mutable recovery ledgers inside the authored plan bundle, inside participant memo pages, or inside runtime-owned recovery files.
