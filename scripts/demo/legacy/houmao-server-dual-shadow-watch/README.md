# Houmao Server Dual Shadow Watch Demo

This pack is the Houmao-owned replacement for the older CAO dual shadow-watch demo.

Its purpose is straightforward: start dedicated server-backed Claude Code and Codex sessions, interactively prompt the live TUIs, and watch how `houmao-server` tracked state changes while you work.

It demonstrates the supported public pair directly:

- `houmao-server` is the live tracking authority
- `houmao-mgr` is the delegated launch CLI

The monitor in this pack does not poll raw CAO output and does not run a demo-local parser, lifecycle reducer, or state tracker. It is a server-state observation surface that renders only what `houmao-server` reports.

## Prerequisites

- `pixi`
- `git`
- `tmux`
- `cao`
- `houmao-server`
- `houmao-mgr`
- `claude`
- `codex`
- usable tool config and credential material under `tests/fixtures/agents/brains/cli-configs/` and `tests/fixtures/agents/brains/api-creds/` for the tracked `projection-demo-*` recipes

The demo uses the copied dummy project fixture at `tests/fixtures/dummy-projects/projection-demo-python`. Neither live agent works in the repository checkout. Each run provisions separate copied git repositories under the run root for Claude and Codex.

## Canonical Workflow

Preflight first:

```bash
scripts/demo/houmao-server-dual-shadow-watch/run_demo.sh preflight --json
```

Start the demo:

```bash
scripts/demo/houmao-server-dual-shadow-watch/run_demo.sh start --json
```

That command:

- provisions isolated Claude and Codex dummy-project workdirs
- builds demo-owned provider homes from the tracked projection-demo recipes
- starts a dedicated `houmao-server` for the run
- launches one Claude session and one Codex session through `houmao-mgr launch`
- starts one monitor tmux session

Attach to the live sessions:

- Claude: `tmux attach -t <claude-session>`
- Codex: `tmux attach -t <codex-session>`
- Monitor: `tmux attach -t <monitor-session>`

Once attached, interactively prompt Claude Code and Codex inside their live TUIs and use the monitor to watch server-tracked state change in real time.
The monitor remains a thin consumer surface: it renders only the tracked state and recent transitions that `houmao-server` publishes for those live sessions.

Inspect a running demo:

```bash
scripts/demo/houmao-server-dual-shadow-watch/run_demo.sh inspect --json
```

`inspect --json` reports timing by ownership:

- `monitor.poll_interval_seconds` is the monitor refresh cadence
- `server.timing_posture.completion_stability_seconds` and `server.timing_posture.unknown_to_stalled_timeout_seconds` are the server posture configured for that run

Stop the run:

```bash
scripts/demo/houmao-server-dual-shadow-watch/run_demo.sh stop --json
```

## Displayed State

The monitor shows server-owned fields for each agent:

- `diagnostics.availability`
- `transport_state`
- `process_state`
- `parse_status`
- `surface.accepting_input`
- `surface.editing_input`
- `surface.ready_posture`
- parsed surface availability, business state, input mode, and UI context
- `turn.phase`
- `last_turn.result`
- `last_turn.source`
- visible-state stability (`stable` / `changing` plus elapsed stable-for time)
- recent anomaly codes

The dashboard header also separates ownership:

- `monitor: poll=...` is the monitor refresh cadence
- `server posture: completion_debounce=... unknown->stalled=...` is the server posture configured for the run

The important public meanings are:

- `diagnostics.availability=available`: the current sample is usable for normal interpretation
- `surface.ready_posture=yes`: the visible surface looks ready to accept immediate submit
- `turn.phase=ready`: the terminal appears ready for another turn now
- `turn.phase=active`: the tracker has enough evidence that a turn is in flight
- `turn.phase=unknown`: the server cannot safely classify the current posture as `ready` or `active`
- `last_turn.result=success|interrupted|known_failure`: the most recent terminal outcome already recorded by the tracker
- `last_turn.source=explicit_input|surface_inference`: whether that recorded turn came from the server-owned input path or inferred direct tmux interaction

The important timing and stability meanings are:

- visible stability: whether the current server-tracked signature has stopped changing, separate from completion debounce timing
- completion debounce: the server-owned settle window that must elapse before a successful ready-looking turn is recorded as `last_turn.result=success`

## Artifacts

Each run keeps deterministic evidence under the run root:

- `control/demo_state.json`
- `control/preflight.json`
- `logs/houmao-server.stdout.log`
- `logs/houmao-server.stderr.log`
- `logs/monitor-dashboard.log`
- `monitor/samples.ndjson`
- `monitor/transitions.ndjson`

`samples.ndjson` contains the server payloads the monitor actually consumed. `transitions.ndjson` contains thin wrappers around server-authored recent transitions.

## Autotest Surfaces

Automatic lifecycle case:

```bash
scripts/demo/houmao-server-dual-shadow-watch/autotest/run_autotest.sh case-preflight-start-stop
```

Interactive staging helper:

```bash
scripts/demo/houmao-server-dual-shadow-watch/autotest/run_autotest.sh case-interactive-shadow-validation
```

Guides:

- `autotest/case-preflight-start-stop.md`
- `autotest/case-interactive-shadow-validation.md`

The automatic case is for fast blocker discovery. The interactive guide remains the primary prompt-and-observe path for watching live server-tracked state transitions.
The helper keeps the historical `case-interactive-shadow-validation` identifier, but the workflow it stages is prompt-and-observe rather than the older validation framing.
