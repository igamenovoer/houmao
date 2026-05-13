## Context

The current skill separates generic execution operations from generated loop artifacts. Generic execution pages can prepare, validate, launch, start, pause, resume, recover, and stop a generated loop when the operator supplies `<loop-dir>` and run identity, but the generated execplan does not yet require a loop-bound control skill that carries the loop identity and lifecycle semantics with it.

The runtime model is mail-notifier-driven: a separate Houmao notifier process detects open mail and prompts agents, and agents must finish each chat turn after bounded event/tick work. Manual operation therefore cannot mean "agents keep waiting in chat"; it must mean the operator disables notifier wakeups and explicitly prompts bounded participant turns.

The existing boundaries still apply:

- generated execplan material owns loop-local semantics;
- generated harness owns dynamic lookup, validation, state, and controlled record application;
- maintained Houmao skills own gateway, mailbox, messaging, launch, workspace, memory, and inspection mechanics;
- generated skills live in one flat `execplan/skills/` namespace.

## Goals / Non-Goals

**Goals:**

- Require a generated `<loop-slug>-operator-control` skill for loop-local lifecycle control when a loop has lifecycle or mode control needs.
- Make loop identity explicit in the generated operator control skill so the operator does not need a global loop identity system.
- Add a generated control contract that distinguishes run lifecycle state from execution mode.
- Make `auto` the default execution mode unless intention source or an accepted operator decision selects another initial mode.
- Make `auto` and `manual` mode queryable through the generated harness.
- Require generated participant on-tick skills to branch on execution mode.
- Keep notifier enable/disable, prompts, mail, and agent lifecycle routed through maintained Houmao operation skills.
- Update validation guidance so generated execplans fail fast when operator control, mode lookup, or mode-aware ticks are missing.

**Non-Goals:**

- Do not introduce a Houmao-wide global loop registry or unified loop identity.
- Do not add new Houmao runtime CLI, gateway API, mailbox API, or managed-agent launch behavior.
- Do not make generated harnesses own mailbox delivery, gateway discovery, notifier implementation, or agent prompting mechanics.
- Do not require manual mode for loops that have no mail-driven participant wakeups or no meaningful operator-directed execution path.

## Decisions

### Generate one loop-local operator control skill

Generated execplans with lifecycle control needs will emit one loop-bound skill named `<loop-slug>-operator-control`. It lives directly under `execplan/skills/` and may contain local subskill/runbook pages such as `status.md`, `start.md`, `set-mode.md`, `pause.md`, `resume.md`, `stop.md`, `recover.md`, and `manual-step.md`.

Alternative considered: generate separate skills such as `<loop-slug>-operator-start`, `<loop-slug>-operator-stop`, and `<loop-slug>-operator-recover`. That fragments loop identity across many installed skills and increases namespace pressure. A single operator control skill with local subpages better matches the flat skill namespace rule.

### Separate run state from execution mode

The generated control contract will treat these as separate axes:

```text
run_state:      not_started | running | paused | recovering | stopped | completed
execution_mode: auto | manual
```

`paused` means normal participant progress is blocked. `manual` means notifier wakeups are disabled or suspended and the operator drives bounded turns directly. A loop can be `running/manual`, `paused/manual`, or `paused/auto`; these states have different recovery and resume behavior.

The default initial `execution_mode` is `auto`. A generated loop should start in `auto` unless the intention source, an accepted clarification decision, or an explicit operator-control action selects another mode.

Alternative considered: encode manual mode as a pause variant. That loses the ability to operate a running loop manually and makes "pause all progress" ambiguous.

### Put mode truth and participant context in the harness

The generated harness should expose control commands such as:

```text
control status
control get-mode --run-id <id>
control set-mode --run-id <id> --mode auto|manual --reason <text>
control pause --run-id <id> --reason <text>
control resume --run-id <id>
control stop --run-id <id> --posture graceful|hard|operator-defined
control manual-context --run-id <id> --participant <id>
```

The output should be machine-readable enough for generated skills, including run state, execution mode, notifier posture, participant identity, pending mail refs, active handoff refs, allowed actions, and a stop-after-one-pass flag when relevant.

Alternative considered: store mode only in generated operator skill prose. That would make per-agent skills unable to reliably branch at runtime and would not provide auditable operator intent events.

### Route platform mechanics through maintained Houmao skills

`<loop-slug>-operator-control` should not implement notifier enable/disable itself. It should record operator intent through the harness, then route notifier posture changes through `houmao-agent-gateway`, prompts through `houmao-agent-messaging`, mail operations through `houmao-agent-email-comms`, and inspection through `houmao-agent-inspect`.

Alternative considered: teach the generated harness to call Houmao gateway or mailbox APIs directly. That breaks the maintained-surface boundary and would duplicate platform contracts inside generated loop artifacts.

### Make on-tick skills mode-aware

Generated on-tick skills should begin by querying the harness for participant control context. In `auto` mode, the tick performs the bounded post-mail scheduling/reconciliation work expected by notifier prompts. In `manual` mode, the tick is operator-prompted and may need to inspect current mail/status/context, process one relevant mail or no-mail action, apply records, send downstream mail or reply upstream, then stop.

Alternative considered: create separate auto-tick and manual-tick skills. That can be useful for complex loops, but the default should keep one participant tick entrypoint and branch on harness context so notifier prompts and operator prompts agree on the participant's bounded work contract.

## Risks / Trade-offs

- Generated operator-control could become too verbose → Keep the required skill concise, use local subpages only for lifecycle procedures that need detail, and point to harness commands and maintained support skills instead of duplicating platform mechanics.
- Manual mode could accidentally become in-chat waiting → Require manual steps to be one bounded operator-prompted pass and require on-tick skills to stop after the pass.
- Mode state and actual gateway notifier posture could diverge → Record both requested mode and observed platform posture in harness/control status, and make validation/reporting show inconsistencies.
- Existing generated examples may use older operator skill names → Treat `<loop-slug>-operator-runbook` as stale example naming and update reference docs toward `<loop-slug>-operator-control`.
- Simple loops may not need all control commands → Allow omitted commands only when the execplan explicitly records the omitted lifecycle area and validation accepts the omission.
