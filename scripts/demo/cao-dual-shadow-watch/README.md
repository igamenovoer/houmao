# CAO Dual Shadow Watch Demo

This pack launches one Claude Code CAO session, one Codex CAO session, and one separate `rich` monitor session so you can manually interact with both TUIs while watching `shadow_only` parser and lifecycle state update every `0.5` seconds.

The pack is standalone. It does not source or invoke sibling demo-pack shell wrappers.

## Purpose

Use this pack to validate live `shadow_only` state transitions, not to benchmark task quality. The monitor is meant to make parser-facing state and runtime-style readiness/completion interpretation visible while you interact with real TUIs.

## Prerequisites

- `pixi` is installed and usable from the repository root.
- `tmux` is installed.
- `cao-server` is installed on `PATH`.
- Your local Claude Code and Codex credential profiles are already configured under the tracked agent-definition setup used by this repository.

## Defaults

- Agent definitions: `tests/fixtures/agents`
- Dummy project fixture: `tests/fixtures/dummy-projects/projection-demo-python`
- Parsing mode: `shadow_only`
- Poll interval: `0.5` seconds
- Completion stability: `1.0` seconds
- Unknown-to-stalled timeout: `30.0` seconds
- Run roots: `tmp/demo/cao-dual-shadow-watch/<timestamp>-<pid>/`

Each started session gets its own copied dummy-project workdir:

- `projects/claude`
- `projects/codex`

Each copied workdir is initialized as a fresh standalone git repository for that run. The live agent sessions do not point at the repository checkout.

## Start

```bash
scripts/demo/cao-dual-shadow-watch/run_demo.sh start
```

Useful overrides:

```bash
scripts/demo/cao-dual-shadow-watch/run_demo.sh start \
  --run-root /tmp/cao-shadow-watch-demo \
  --poll-interval-seconds 0.5 \
  --completion-stability-seconds 1.0 \
  --unknown-to-stalled-timeout-seconds 30.0
```

The start output prints:

- the selected run root
- the shared CAO base URL and profile store
- one attach command for the Claude session
- one attach command for the Codex session
- one attach command for the monitor session

## Inspect

```bash
scripts/demo/cao-dual-shadow-watch/run_demo.sh inspect
scripts/demo/cao-dual-shadow-watch/run_demo.sh inspect --json
```

Without `--run-root`, `inspect` uses the latest recorded run root pointer.

## Attach

Open three terminals and attach to the printed tmux sessions:

- Claude session
- Codex session
- monitor session

The monitor separates raw parser fields from higher-level lifecycle state:

- parser fields:
  - `availability`
  - `business_state`
  - `input_mode`
  - `ui_context`
- lifecycle fields:
  - `readiness`
  - `completion`
- auxiliary fields:
  - `projection_changed`
  - `baseline_invalidated`
  - `anomalies`

## Expected State Meanings

- `readiness=ready`: submit-ready prompt surface
- `readiness=waiting`: known non-ready surface such as menus or modal input
- `readiness=blocked`: operator intervention required
- `readiness=failed`: disconnected or unsupported surface
- `readiness=unknown`: parser cannot classify the surface for stall purposes
- `readiness=stalled`: unknown state persisted long enough to cross the timeout

- `completion=inactive`: no completion watch is currently armed
- `completion=in_progress`: post-submit work is still happening
- `completion=candidate_complete`: submit-ready again, but still within the stability window
- `completion=completed`: submit-ready and stable for the full completion window
- `completion=blocked|failed|unknown|stalled`: corresponding live surface condition

## Manual Validation Exercises

Use short prompts so state changes are easy to observe:

1. Let both sessions settle at an idle prompt and confirm `readiness=ready`.
2. Open a slash-command or selection menu and confirm `readiness=waiting`.
3. Trigger a trust prompt, approval prompt, or similar confirmation surface and confirm `blocked`.
4. Submit a short question about the dummy project, then watch `completion` move through `in_progress -> candidate_complete -> completed`.
5. While the answer is stabilizing, interact again so the normalized projection changes and confirm the completion window resets.
6. If a parser surface becomes unclassifiable long enough, confirm `unknown -> stalled`.

## Artifacts

Each run root persists:

- `control/demo_state.json`
- `monitor/samples.ndjson`
- `monitor/transitions.ndjson`
- `logs/monitor-dashboard.log`

These are preserved after `stop`.

## Stop

```bash
scripts/demo/cao-dual-shadow-watch/run_demo.sh stop
```

This stops both runtime sessions, terminates the monitor tmux session, and preserves the run artifacts for later inspection.
