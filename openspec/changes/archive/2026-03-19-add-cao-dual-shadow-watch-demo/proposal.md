## Why

The current repo has CAO demo packs and shadow parser/runtime coverage, but it does not provide one standalone operator demo where Claude Code and Codex are both launched by houmao, manually driven in their live TUIs, and observed side-by-side through continuously updating shadow-state diagnostics. That gap makes it harder to validate whether the `shadow_only` parser and Rx lifecycle detection behave correctly during real interactive use rather than only in automated tests or single-agent walkthroughs.

## What Changes

- Add a standalone demo pack under `scripts/demo/` for launching one Claude Code CAO session and one Codex CAO session from houmao without depending on other demo-pack scripts.
- Provision a demo-owned dummy project fixture into the run root and use isolated copies of that fixture as the agent workdirs for the Claude and Codex sessions.
- Start both agents in `cao_rest` with `--cao-parsing-mode shadow_only` and surface attach commands so the operator can manually interact with each live TUI.
- Add a separate monitor process and tmux session that polls both live terminals every 0.5 seconds, parses `mode=full` output through the runtime shadow parser stack, and renders an easy-to-read `rich` dashboard for the detected parser and lifecycle states.
- Persist machine-readable monitor artifacts so state transitions and parser anomalies can be inspected after the demo run.
- Document the standalone workflow, prerequisites, and manual validation steps for the demo pack.

## Capabilities

### New Capabilities
- `cao-dual-shadow-watch-demo`: Standalone dual-agent CAO demo workflow that launches Claude and Codex in `shadow_only`, uses demo-owned dummy-project workdirs, and renders live shadow-state monitoring for operator validation.

### Modified Capabilities
- None.

## Impact

- Adds a new standalone demo pack under `scripts/demo/` plus operator-facing documentation and run artifacts under `tmp/demo/`.
- Reuses existing runtime and parser modules such as `realm_controller`, CAO server launcher integration, `ShadowParserStack`, and the Rx shadow-monitor semantics, but does not depend on other demo-pack wrapper scripts.
- Relies on the tracked dummy-project fixture under `tests/fixtures/dummy-projects/` for predictable demo workdirs.
- Uses `rich` for the live monitoring dashboard; the dependency already exists in the repository environment.
