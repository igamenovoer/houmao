# Terminal Recorder Architecture

This page explains the maintained architecture of the terminal recorder and the invariants that downstream parser/state-tracking tooling depends on.

## Core Invariants

The current design depends on these rules.

1. The recorder targets an existing tmux session or explicit pane. It does not launch the agent it records.
2. `session.cast` is an operator-facing artifact, not the machine replay source of truth.
3. `pane_snapshots.ndjson` is the authoritative replay surface for parser and state-tracking analysis.
4. `active` and `passive` are different contracts, not cosmetic modes.
5. Managed `send-keys` logging is additive. Recorder failures must not block successful tmux control-input delivery.

If a proposed change breaks one of those rules, it should first be treated as a design change and reflected back into OpenSpec/docs/tests.

## Lifecycle Model

The long-running controller process owns one recorder run root.

Start flow:

1. Resolve the target tmux session and pane. If a session has multiple panes and no explicit pane is given, fail instead of guessing.
2. Persist `manifest.json` and `live_state.json`.
3. Spawn the controller process.
4. Launch a recorder-owned tmux session that runs `pixi run asciinema record ...`.
5. Begin the sampling loop against the target pane using `tmux capture-pane`.

During the run:

- active mode surfaces a recorder-owned attach path and publishes `HOUMAO_TERMINAL_RECORD_LIVE_STATE` into the target tmux session
- passive mode attaches read-only for visual observation and does not claim exclusive input ownership
- the sampling loop continuously appends exact pane content to `pane_snapshots.ndjson`
- active mode degrades from `authoritative_managed` to `managed_only` if extra tmux clients attach and taint the run

Stop flow:

1. Persist a stop request through `live_state.json`.
2. Capture one final pane snapshot before finalization.
3. Stop the recorder tmux session.
4. In active mode, merge `asciinema` input frames into `input_events.ndjson` and clear the tmux session env publication.
5. Finalize `manifest.json` and `live_state.json` without deleting artifacts.

## Artifact Authority Boundaries

The recorder intentionally separates visual review from machine replay.

Human-facing artifacts:

- `session.cast`
- `asciinema.log`
- `controller.log`

Replay-grade artifacts:

- `pane_snapshots.ndjson`
- `input_events.ndjson` when `input_capture_level` is `authoritative_managed` or `managed_only`
- `parser_observed.ndjson`
- `state_observed.ndjson` using the official tracked-state vocabulary for diagnostics posture, `surface`, `turn`, and `last_turn`
- `labels.json`

The most important downstream rule is simple: parser/state replay should use pane snapshots, not cast reconstruction.

`terminal_record add-label` remains the primary repo-owned label-authoring surface. Replay-grade labels should target official tracked-state fields such as diagnostics posture, `surface_accepting_input`, `turn_phase`, `last_turn_result`, and `last_turn_source` rather than older readiness/completion names.

## Runtime Integration Points

The recorder integrates with two runtime surfaces.

Shared tmux helpers in `tmux_runtime.py`:

- target discovery through `list_tmux_panes()`
- capture through `capture_tmux_pane()`
- client counting through `list_tmux_clients()`
- tmux session env publication helpers

Managed control input in `cao_rest.py`:

- `CaoRestSession.send_input_ex()` still parses and delivers tmux control input first
- after successful delivery it calls `append_managed_control_input_for_tmux_session()`
- the runtime bridge reads the recorder live-state pointer from the target tmux session env
- only active recorder runs append `managed_send_keys` events

That integration is intentionally narrow. Arbitrary third-party tmux clients or unrelated `tmux send-keys` calls are outside the recorder’s authoritative managed-input contract.
