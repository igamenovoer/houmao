# Interactive CAO Demo

This page is the docs-side overview for the interactive Claude-on-CAO demo pack under `scripts/demo/cao-interactive-full-pipeline-demo/`. Use it when you want the big picture for the wrapper workflow, artifact layout, and implementation modules without reading the full step-by-step tutorial first.

For the full operator walkthrough, examples, and troubleshooting flow, see [Interactive CAO Full-Pipeline Tutorial Pack](../../scripts/demo/cao-interactive-full-pipeline-demo/README.md).

## What The Demo Covers

The demo keeps one long-running CAO-backed Claude session alive under the wrapper-friendly name `alice`, persists the canonical runtime identity as `AGENTSYS-alice`, and lets you:

- launch or replace the interactive session
- inspect the live session and attach to tmux
- send normal prompt turns
- send raw control input with `send-keys`
- stop the session explicitly
- optionally run maintainer-only `verify`

The workflow is intentionally pinned to `http://127.0.0.1:9889` and uses a fresh per-run workspace under `tmp/demo/cao-interactive-full-pipeline-demo/<ts>/`.

## Main Command Surfaces

- `scripts/demo/cao-interactive-full-pipeline-demo/launch_alice.sh`: launch or replace the tutorial session as `alice`
- `scripts/demo/cao-interactive-full-pipeline-demo/send_prompt.sh --prompt "<text>"`: send one prompt turn and capture a normal turn artifact
- `scripts/demo/cao-interactive-full-pipeline-demo/send_keys.sh '<[Escape]>'`: send one raw control-input sequence without creating a prompt turn
- `scripts/demo/cao-interactive-full-pipeline-demo/stop_demo.sh`: stop the active session and mark local state inactive
- `scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh inspect`: print the live session summary, tmux attach command, and terminal-log tail command
- `scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh verify`: run the optional maintainer regression check after at least two prompt turns

## Prompt Turns Versus Control Input

The demo now distinguishes normal prompt traffic from raw control input:

- `send_prompt.sh` records prompt/response artifacts under `turns/`
- `send_keys.sh` and `run_demo.sh send-keys ...` record control-input artifacts under `controls/`
- control-input actions do not count as prompt turns for `verify`

Use `send-keys` when you need to drive a live TUI surface rather than submit a normal prompt, for example to send `Escape`, drive a slash-command menu, type partial text without auto-submit, or pass token-like text literally with `--as-raw-string`.

For the low-level `send-keys` grammar and exact token rules, see [Brain Launch Runtime Send-Keys](./brain_launch_runtime_send_keys.md).

## Artifact Layout

The per-run workspace keeps the major artifact families separate:

- `state.json`: active-session identity and metadata
- `turns/turn-*.json`: prompt-turn artifacts
- `controls/control-*.json`: control-input records plus related stdout/stderr logs
- `report.json`: optional maintainer verification report
- `current_run_root.txt`: marker used by wrapper commands to find the current run root when `DEMO_WORKSPACE_ROOT` is not supplied

This separation is intentional so manual control input can coexist with later prompt turns without corrupting the verification contract.

## Implementation Layout

The interactive demo implementation no longer lives in one monolithic module. The canonical package is `gig_agents.demo.cao_interactive_demo`.

| Module | Responsibility |
| --- | --- |
| `__init__.py` | Re-export the public API for the package |
| `models.py` | Data models, dataclasses, constants, and shared type aliases |
| `cli.py` | CLI parser, argument resolution, and top-level command dispatch |
| `commands.py` | Public workflow functions such as `start_demo`, `send_turn`, `send_control_input`, `inspect_demo`, `verify_demo`, and `stop_demo` |
| `cao_server.py` | CAO server lifecycle helpers and fixed-loopback startup management |
| `runtime.py` | Brain build, runtime session start/stop, and subprocess helpers |
| `rendering.py` | Human-readable output rendering, JSON parsing helpers, and output-tail utilities |

This split makes it easier to patch or test one concern at a time while keeping the wrapper scripts stable.

## How It Connects To The Runtime

The demo wrappers sit above the repo-owned runtime stack:

1. Wrapper scripts delegate to `run_demo.sh`.
2. `run_demo.sh` invokes `pixi run python -m gig_agents.demo.cao_interactive_demo.cli`.
3. The demo package uses `gig_agents.agents.brain_launch_runtime` for `start-session`, `send-prompt`, `send-keys`, and `stop-session`.
4. CAO-backed runtime state provides the persisted session identity and tmux-resolution data needed for follow-up prompt and control-input actions.

For the lower-level runtime contract, see [Brain Launch Runtime](./brain_launch_runtime.md).
