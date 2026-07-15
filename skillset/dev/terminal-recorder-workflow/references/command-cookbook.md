# Terminal Recorder Command Cookbook

## Quick Start

Run every recorder command from the repository root with Pixi:

```bash
pixi run python -m tools.terminal_record --help
```

Subcommands:

- `start`
- `status`
- `stop`
- `analyze`
- `add-label`

## Target Discovery

List sessions:

```bash
tmux list-sessions
```

List panes with useful fields:

```bash
tmux list-panes -a -F '#{session_name}\t#{window_name}\t#{pane_id}\t#{pane_current_command}'
```

Use `--target-pane` whenever the target session has more than one pane.

## Mode Selection

### Passive

Use `passive` to observe a live session without claiming the input path.

```bash
pixi run python -m tools.terminal_record start \
  --mode passive \
  --target-session gig-3 \
  --target-pane %19 \
  --tool claude
```

Properties:

- visual recording only
- `input_capture_level=output_only`
- good default for manual observation and TUI pattern study

### Active

Use `active` when you want recorder-owned attach behavior and managed `send-keys` logging.

```bash
pixi run python -m tools.terminal_record start \
  --mode active \
  --target-session HOUMAO-gpu \
  --tool codex
```

Properties:

- publishes recorder live state back into the target tmux session
- captures managed repo `send-keys` events when available
- may degrade from `authoritative_managed` to `managed_only` if the run is tainted by extra tmux clients

## Run Lifecycle

Inspect a run:

```bash
pixi run python -m tools.terminal_record status \
  --run-root tmp/terminal_record/<run-id>
```

Stop a run:

```bash
pixi run python -m tools.terminal_record stop \
  --run-root tmp/terminal_record/<run-id>
```

Analyze a finished run:

```bash
pixi run python -m tools.terminal_record analyze \
  --run-root tmp/terminal_record/<run-id>
```

Add a structured label:

```bash
pixi run python -m tools.terminal_record add-label \
  --run-root tmp/terminal_record/<run-id> \
  --label-id trust-prompt-blocked \
  --scenario-id trust-prompt-recovery \
  --sample-id s000021 \
  --business-state awaiting_operator \
  --readiness-state blocked
```

## Artifact Map

Each run root lives under `tmp/terminal_record/<run-id>/` unless `--run-root` overrides it.

Important files:

- `manifest.json`: recorder mode, target, taint metadata, timing metadata, attach command
- `live_state.json`: controller status used by `status` and `stop`
- `session.cast`: human review artifact
- `pane_snapshots.ndjson`: authoritative replay surface
- `input_events.ndjson`: managed input events when the mode supports them
- `parser_observed.ndjson`: parser observations written by `analyze`
- `state_observed.ndjson`: state-tracker observations written by `analyze`
- `labels.json`: durable operator labels

## Practical Reading Order

When debugging TUI state tracking:

1. Read `manifest.json` to confirm mode, target, and taint.
2. Read `pane_snapshots.ndjson` first.
3. Run `analyze`.
4. Compare `parser_observed.ndjson` and `state_observed.ndjson` back to the raw pane snapshots.
5. Add labels for the important samples you want to preserve.

## Common Mistakes

- Using `session.cast` as machine truth instead of `pane_snapshots.ndjson`
- Forgetting `--target-pane` for multi-pane sessions
- Leaving a recorder live and then wondering why a later run collides with the old `run_root`
- Assuming `active` and `passive` are interchangeable
- Treating `analyze` output as the source of truth when the raw pane sequence disagrees
