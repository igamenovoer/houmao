# Houmao Server Dual Shadow Watch Demo

This pack is the Houmao-owned replacement for the older CAO dual shadow-watch demo.

It validates the supported public pair directly:

- `houmao-server` is the live tracking authority
- `houmao-srv-ctrl` is the delegated launch CLI

The monitor in this pack does not poll raw CAO output and does not run a demo-local parser or lifecycle reducer. It renders only what `houmao-server` reports.

## Prerequisites

- `pixi`
- `git`
- `tmux`
- `cao`
- `houmao-server`
- `houmao-srv-ctrl`
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
- starts a demo-owned `houmao-server`
- installs the tracked `projection-demo` profile into the demo-owned CAO home
- launches one Claude session and one Codex session through `houmao-srv-ctrl launch`
- starts one monitor tmux session

Attach to the live sessions:

- Claude: `tmux attach -t <claude-session>`
- Codex: `tmux attach -t <codex-session>`
- Monitor: `tmux attach -t <monitor-session>`

Inspect a running demo:

```bash
scripts/demo/houmao-server-dual-shadow-watch/run_demo.sh inspect --json
```

Stop the run:

```bash
scripts/demo/houmao-server-dual-shadow-watch/run_demo.sh stop --json
```

## Displayed State

The monitor shows server-owned fields for each agent:

- `transport_state`
- `process_state`
- `parse_status`
- parser availability, business state, input mode, and UI context
- readiness state
- completion state
- projection-change indicator
- lifecycle timing for unknown and candidate-complete windows
- recent anomaly codes

The important lifecycle meanings are:

- `ready`: prompt-submit ready
- `in_progress`: working after a previously ready baseline
- `candidate_complete`: looks complete but is still inside the completion stability window
- `completed`: candidate-complete remained stable for `completion_stability_seconds`
- `blocked`: operator interaction is required
- `unknown`: parser surface is not yet classifiable
- `stalled`: unknown remained continuous long enough to cross `unknown_to_stalled_timeout_seconds`

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

The automatic case is for fast blocker discovery. The interactive guide remains the primary validation path for live state transitions.
