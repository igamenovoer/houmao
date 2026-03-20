# Codex Activity State Signals

## Context

- Source-inspected on 2026-03-20
- Tool: Codex TUI (app-server variant)
- Local source checkout: `extern/orphan/codex`
- Source revision: `fa2a2f0be94e744d6d565a803e12c870d283f930`
- Workspace Cargo version: `0.0.0`
- Primary source artifacts:
  - `extern/orphan/codex/codex-rs/tui_app_server/src/chatwidget.rs`
  - `extern/orphan/codex/codex-rs/tui_app_server/src/status_indicator_widget.rs`
  - `extern/orphan/codex/codex-rs/tui_app_server/src/history_cell.rs`
  - `extern/orphan/codex/codex-rs/tui_app_server/src/streaming/controller.rs`
  - `extern/orphan/codex/codex-rs/tui_app_server/src/bottom_pane/mod.rs`
  - `extern/orphan/codex/codex-rs/tui_app_server/src/snapshots/codex_tui_app_server__status_indicator_widget__tests__renders_with_working_header.snap`
  - `extern/orphan/codex/codex-rs/tui_app_server/src/bottom_pane/snapshots/codex_tui_app_server__bottom_pane__tests__status_only_snapshot.snap`
  - `extern/orphan/codex/codex-rs/tui_app_server/src/snapshots/codex_tui_app_server__history_cell__tests__active_mcp_tool_call_snapshot.snap`
  - `extern/orphan/codex/codex-rs/tui_app_server/src/chatwidget/snapshots/codex_tui_app_server__chatwidget__tests__unified_exec_wait_before_streamed_agent_message.snap`
- Intent: define Codex-specific active-turn and ready/success return signals directly from renderer and state-management code, then check them against one real tmux recording

## Source-Derived Model Facts

The Codex bottom status row is a shared busy indicator, not a pure turn indicator.

The source explicitly states that the bottom pane is considered "running" while either of these is true:

- an agent turn is in progress (`agent_turn_running`)
- MCP server startup is in progress (`mcp_startup_status.is_some()`)

So a generic visible busy row is not enough by itself to prove `turn_active`.

The source also explicitly states that assistant output streaming can hide the status row:

- during streaming, the TUI hides the status row to avoid duplicate progress indicators
- while that happens, in-flight assistant transcript content is still being appended through `StreamController` and `AgentMessageCell`

So Codex active-turn detection MUST support both:

- active status-row surfaces
- active transcript-growth surfaces

## Live Validation

One real Codex tmux session was passively recorded on 2026-03-20:

- tmux session: `cao-houmao-shadow-watch-live-interactive-20260320-004350-codex`
- recorder run root: `tmp/terminal_record/codex-signal-check-20260320/`

Live samples from that run matched the source-derived model and added two practical clarifications:

- `s000156` through `s000247`: a non-empty composer draft remained visible for many samples before submit, but no turn had started yet. A typed prompt alone is not `turn_active`.
- `s000248`: after explicit submit, the pane showed a visible `Working (0s • esc to interrupt)` row with no assistant transcript yet.
- `s000282` and `s000284`: streamed transcript progress and the `Working` row coexisted in the same latest-turn surface.
- `s000951`: the pane showed `Model interrupted to submit steer instructions.` immediately followed by a fresh submitted prompt and a new `Working` row. That is a steer-handoff surface for a new active turn, not a terminal interrupted-ready result.

The same recording also showed that current analyzer output is not yet sufficient to replace raw-pane evidence:

- `state_observed.ndjson` still classified visible `Working` samples such as `s000248`, `s000282`, and `s000951` as `business_state=idle` and `readiness_state=ready`
- for spec work, the raw pane snapshots remain the stronger authority

## State: `turn_active`

### Classification

When the active-turn signal matches, the tracked current turn state is:

- current posture: `turn_active`

### Sufficient Evidence

Any one of the signal groups below is sufficient active-turn evidence for the current surface.

#### A. Agent-turn status row

All of the following are true in the same current surface:

1. A visible Codex status row matches the `StatusIndicatorWidget` structure `• <header> (<elapsed> • esc to interrupt)` or the same row with wrapped detail lines below it
2. The header is an agent-turn-backed header, not an MCP-startup-only header
3. No modal bottom-pane view is currently covering the status row

Agent-turn-backed headers confirmed by source inspection include:

- `Working`
- a reasoning-derived header extracted from the first bold segment of live reasoning output
- `Waiting for background terminal`
- `Reviewing approval request`
- `Reviewing <n> approval requests`

Representative source-backed surface:

```text
• Working (0s • esc to interrupt)

› Ask Codex to do anything

  ? for shortcuts            100% context left
```

Representative detail-bearing variant:

```text
• Working (0s • esc to interrupt)
  └ First detail line
    Second detail line
```

#### B. In-flight tool or command transcript cell

Any one of the following is visible in the latest relevant transcript region for the current turn:

- an in-flight MCP tool cell headed by `Calling ...`
- an in-flight exec cell headed by `Running ...`
- a just-flushed unified-exec wait cell such as `Waited for background terminal · <command>` while the turn still remains in progress

Representative source-backed surfaces:

```text
• Calling search.find_docs({"query":"ratatui styling","limit":3})
```

```text
• Waited for background terminal · cargo test -p codex-core
```

Interpretation:

- these are produced by in-flight turn work rather than idle ready posture
- they are stronger turn-activity signals than local editor popups

#### C. Visible assistant answer or plan growth while the status row is hidden

All of the following are true:

1. The latest assistant transcript content is visibly growing across observations
2. The turn has not yet shown a terminal interruption or latest-turn error signal
3. The surface has not yet settled back to a ready composer posture

This rule is a direct inference from source, not from a rendered snapshot alone:

- `chatwidget.rs` explicitly says the status row is hidden during streaming
- `StreamController` appends streamed assistant content as `AgentMessageCell`s while the turn is still active

Interpretation:

- Codex can be actively answering even when the busy row is absent
- transcript growth must therefore count as active-turn evidence

#### D. Steer-resubmission handoff

All of the following are true:

1. The latest relevant transcript region contains the exact informational line `Model interrupted to submit steer instructions.`
2. A fresh submitted prompt for a newer turn is visible below that line
3. A current agent-turn-backed status row is visible for that newer prompt

Representative live-validated surface from recorder sample `s000951`:

```text
• Model interrupted to submit steer instructions.

› Run `sleep 30` in the shell, then respond with AFTERSLEEP only.

• Working (0s • esc to interrupt)
```

Interpretation:

- the previous response was preempted so a new prompt could start immediately
- the current state is `turn_active` for the new turn
- this surface MUST NOT be collapsed to terminal `turn_interrupted`

### Non-Turn Busy Rows

The following visible status headers are busy surfaces but MUST NOT be treated as `turn_active` from this note alone:

- `Booting MCP server: <name>`
- `Starting MCP servers (<completed>/<total>): ...`

Reason:

- the source drives those headers from `mcp_startup_status`, which is separate from `agent_turn_running`
- they indicate tool/bootstrap activity, not necessarily a submitted Codex turn

### Local Editing Overlay Rule

Local composer overlays do NOT by themselves create or cancel turn activity.

Examples from source and snapshots:

- slash-command popup after typing `/`
- skill popup after typing `$`
- plugin/app mention popup

Interpretation:

- those are local editor surfaces
- tests explicitly verify that pressing `Esc` on those popups dismisses the popup instead of interrupting the running task
- if stronger active-turn evidence remains visible, the classification stays `turn_active`
- popup visibility alone does not imply `turn_active`

## State: `turn_ready` with `last_turn=success`

### Classification

When the successful-return signal matches, the tracked states are:

- current posture: `turn_ready`
- last turn outcome: `success`

### Required Conditions

All conditions below MUST be true in the same current surface:

1. No modal approval / request-user-input / MCP-elicitation / app-link suggestion view is active
2. No agent-turn status row is currently visible
3. The composer is visible and accepting input, with a prompt row beginning with `›`
4. The current visible TUI has remained stable for a short settle window such as `1s`
5. No current latest-turn red `■ ...` error cell is present
6. No current exact interruption surface from the dedicated interruption note is present
7. The latest turn previously had stronger active-turn evidence or was known to have been submitted

Representative ready surface:

```text
› Ask Codex to do anything

  ? for shortcuts            100% context left
```

### Optional Supporting Success Marker

If the latest completed turn performed concrete work, Codex may also render a final separator line of the form:

```text
─ Worked for 1m 01s ─
```

or a separator that includes runtime metrics such as local-tool or inference timing.

That separator is supporting evidence only:

- it helps confirm a completed work-bearing turn
- it MUST NOT be required for success, because short or purely conversational turns may omit it
- it MUST NOT override a current latest-turn interruption or red error surface

## Non-Match Guidance

- Do not classify `turn_active` from a generic busy row unless the header is agent-turn-backed rather than MCP-startup-only
- Do not classify `turn_active` from slash / skill / plugin popups alone
- Do not classify `turn_active` from a non-empty typed composer draft alone before explicit submit
- Do not classify `turn_ready` with `last_turn=success` while a modal overlay is active
- Do not classify `turn_ready` with `last_turn=success` while the latest-turn red `■ ...` error cell is present
- Do not require the `Worked for ...` separator to recognize success
- Do not let a stale older error cell in scrollback block a later settled ready surface for a newer turn
- Do not miss active turns just because the status row is hidden during live assistant streaming
- Do not emit terminal interruption from `Model interrupted to submit steer instructions.` when the same current surface has already moved into a new active turn

## Current Design Implications

- Codex active-turn detection must distinguish agent-turn headers from MCP-startup headers
- Codex active-turn detection cannot depend only on the status row, because streaming deliberately hides it
- Local editing popups are not reliable lifecycle signals
- Codex success is primarily a stable return to ready posture, optionally supported by a `Worked for ...` separator, not by one universal completion banner
