# Interactive CAO Demo

This page is the docs-side overview for the interactive CAO full-pipeline demo pack under `scripts/demo/cao-interactive-full-pipeline-demo/`. Use it when you want the big picture for the wrapper workflow, recipe-backed startup contract, artifact layout, and implementation modules without reading the full step-by-step tutorial first.

For the full operator walkthrough, examples, and troubleshooting flow, see [Interactive CAO Full-Pipeline Tutorial Pack](../../scripts/demo/cao-interactive-full-pipeline-demo/README.md).

## What The Demo Covers

The pack keeps one long-running CAO-backed session alive at a time and supports both Claude and Codex through tracked brain recipes.

- Default implicit startup: `claude/gpu-kernel-coder-default`
- Explicit Claude startup: `run_demo.sh start --brain-recipe claude/gpu-kernel-coder-default`
- Explicit Codex startup: `run_demo.sh start --brain-recipe codex/gpu-kernel-coder-default`
- Explicit Codex Yunwu startup: `run_demo.sh start --brain-recipe codex/gpu-kernel-coder-yunwu-openai`

Direct `run_demo.sh start` uses the selected recipe's `default_agent_name` unless the operator supplies `--agent-name`. `launch_alice.sh` is only a convenience wrapper that injects `--agent-name alice`.

The workflow is intentionally pinned to `http://127.0.0.1:9889` and uses a fresh per-run workspace under `tmp/demo/cao-interactive-full-pipeline-demo/<ts>/`.

## Main Command Surfaces

- `scripts/demo/cao-interactive-full-pipeline-demo/launch_alice.sh`: launch or replace the tutorial session as `alice`, with optional `--brain-recipe`
- `scripts/demo/cao-interactive-full-pipeline-demo/send_prompt.sh --prompt "<text>"`: send one prompt turn and capture a normal turn artifact
- `scripts/demo/cao-interactive-full-pipeline-demo/send_keys.sh '<[Escape]>'`: send one raw control-input sequence without creating a prompt turn
- `scripts/demo/cao-interactive-full-pipeline-demo/stop_demo.sh`: stop the active session and mark local state inactive
- `scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh inspect`: print live session summary, selected tool and variant, tmux attach command, and terminal-log tail command
- `scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh verify`: run the optional maintainer regression check after at least two prompt turns

## Recipe Resolution Rules

Selectors are resolved relative to `brains/brain-recipes/` under the active agent-definition directory. `.yaml` is optional.

- Unique basenames are allowed, for example `gpu-kernel-coder-yunwu-openai`
- Subdirectory selectors are always allowed, for example `codex/gpu-kernel-coder-default`
- Ambiguous basenames fail explicitly and ask the operator to retry with subdirectory context

The demo persists the resolved `tool`, canonical `brain_recipe`, and normalized `variant_id` in `state.json`, and all follow-up commands reuse that persisted variant metadata.

## Prompt Turns Versus Control Input

The demo keeps prompt turns and raw control input separate:

- `send_prompt.sh` records prompt/response artifacts under `turns/`
- `send_keys.sh` and `run_demo.sh send-keys ...` record control-input artifacts under `controls/`
- control-input actions do not count as prompt turns for `verify`

## Inspect And Verify Surfaces

`inspect` now exposes tool-aware metadata:

- `tool`
- `variant_id`
- `brain_recipe`
- `tool_state`

When `inspect --with-output-text <n>` is requested, the demo fetches CAO `mode=full` output and projects it through the runtime-owned parser stack for the persisted tool. Claude launches use the Claude parser and Codex launches use the Codex parser.

`verify` writes `report.json` and validates a sanitized shape against the variant-specific fixture under `scripts/demo/cao-interactive-full-pipeline-demo/expected_report/<variant-id>.json`.

## Artifact Layout

The per-run workspace keeps the major artifact families separate:

- `state.json`: active-session identity plus persisted recipe/tool metadata
- `turns/turn-*.json`: prompt-turn artifacts
- `controls/control-*.json`: control-input records plus related stdout/stderr logs
- `report.json`: optional maintainer verification report
- `current_run_root.txt`: marker used by wrapper commands to find the current run root when `DEMO_WORKSPACE_ROOT` is not supplied

## Implementation Layout

The canonical package is `gig_agents.demo.cao_interactive_demo`.

| Module | Responsibility |
| --- | --- |
| `brain_recipes.py` | Fixed-root recipe selector resolution, canonicalization, ambiguity handling |
| `models.py` | Data models, dataclasses, constants, and shared type aliases |
| `cli.py` | CLI parser, argument resolution, and top-level command dispatch |
| `commands.py` | Public workflow functions such as `start_demo`, `send_turn`, `send_control_input`, `inspect_demo`, `verify_demo`, and `stop_demo` |
| `cao_server.py` | CAO server lifecycle helpers and fixed-loopback startup management |
| `runtime.py` | Brain build, runtime session start/stop, subprocess helpers, and parser-stack selection |
| `rendering.py` | Human-readable output rendering, JSON parsing helpers, and output-tail utilities |

## How It Connects To The Runtime

1. Wrapper scripts delegate to `run_demo.sh`.
2. `run_demo.sh` invokes `pixi run python -m gig_agents.demo.cao_interactive_demo.cli`.
3. The demo package resolves the selected brain recipe under `tests/fixtures/agents/brains/brain-recipes/` (or the overridden agent-definition directory).
4. The demo delegates brain construction through `gig_agents.agents.brain_launch_runtime build-brain --recipe <resolved-path>`.
5. The demo uses `gig_agents.agents.brain_launch_runtime` for `start-session`, `send-prompt`, `send-keys`, and `stop-session`.

For the lower-level runtime contract, see [Brain Launch Runtime](./brain_launch_runtime.md).
