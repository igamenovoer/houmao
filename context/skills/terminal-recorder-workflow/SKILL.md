---
name: terminal-recorder-workflow
description: Use when Codex needs to capture, inspect, stop, analyze, or label an already-running tmux-backed agent session with the repo terminal recorder under `tools/terminal_record`, especially for parser/state-tracking investigation, replay-grade TUI artifact capture, or documenting observed terminal signals.
---

# Terminal Recorder Workflow

Use the repo-managed CLI, not the service module directly:

```bash
pixi run python -m tools.terminal_record ...
```

Treat recorder artifacts with the right authority boundary:

- Use `pane_snapshots.ndjson` as the machine replay source of truth.
- Use `session.cast` for human review only.
- Use `parser_observed.ndjson` and `state_observed.ndjson` only after `analyze`.

## Workflow

1. Discover the tmux target before starting the recorder.

Use `tmux list-sessions` and `tmux list-panes -a -F '#{session_name}\t#{window_name}\t#{pane_id}\t#{pane_current_command}'` to find the exact session and pane. If the target session has multiple panes, pass `--target-pane`; do not guess.

2. Choose `active` or `passive`.

- Use `passive` when you are observing an already-running session and do not want the recorder to own the input path.
- Use `active` when you want recorder-managed attach behavior and repo-managed `send-keys` integration.
- Expect `active` input capture to degrade if extra tmux clients attach to the target session.

3. Start the run and keep the returned `run_root`.

Start from repo root. The recorder writes under `tmp/terminal_record/<run-id>/` unless `--run-root` overrides it. The `run_root` is the handle you need for `status`, `stop`, `analyze`, and `add-label`.

4. Inspect or drive the session while the recorder is live.

- Use `status` to confirm controller liveness.
- In `active` mode, prefer the recorder-owned attach path if you need to attach interactively.
- If you are studying TUI patterns, keep notes about the samples or timestamps you care about so you can label them later.

5. Stop the run before analyzing artifacts.

Use `stop` with the same `run_root`. Do not assume recorder shutdown from pane exit alone.

6. Analyze the run when you need parser or tracker views.

Run `analyze` on the finished run root to emit `parser_observed.ndjson` and `state_observed.ndjson`. Compare them against `pane_snapshots.ndjson` when you are debugging parser or lifecycle mistakes.

7. Label checkpoints when you need durable signal notes.

Use `add-label` to persist sample-level or scenario-level annotations into `labels.json`.

## Read More

- Read [references/command-cookbook.md](references/command-cookbook.md) for exact command shapes, artifact names, and common operator decisions.
- Read [docs/reference/terminal_record.md](/data1/huangzhe/code/houmao/docs/reference/terminal_record.md) when you need the maintained command and artifact contract.
- Read [docs/developer/terminal-record/index.md](/data1/huangzhe/code/houmao/docs/developer/terminal-record/index.md) when you are changing recorder behavior rather than just using it.

## Guardrails

- Do not treat `session.cast` as replay-grade machine evidence.
- Do not start recording before confirming the tmux target; ambiguous sessions should be resolved explicitly.
- Do not forget to stop the recorder; `status` and `stop` operate on persisted run state, not just a live pane.
- Do not assume slash-menu churn, repaint, or transcript leftovers explain current state. Check the raw `pane_snapshots.ndjson` sequence.
