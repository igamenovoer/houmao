## Why

The current `houmao-server` interactive shadow-watch path is failing in a way that cannot be resolved by inspection alone: direct live prompts visibly execute, but the server-tracked lifecycle surface stays `ready` / `inactive` / `unanchored_background`. We need a repeatable, no-guess debugging workflow that records exactly how prompt submission, parser observations, lifecycle reduction, and transition publishing behave on both the server-owned input path and the direct tmux-input path.

## What Changes

- Add a maintainer-facing debug workflow for `houmao-server` live TUI tracking that injects dense, env-gated tracing around prompt submission, turn-anchor arming, parsed-surface observation, lifecycle reduction, operator-state construction, stability calculation, and transition publication.
- Add an automatic repro runner that exercises both:
  - a server-owned prompt submission path, and
  - a direct interactive tmux-input path,
  against the same `houmao-server` shadow-watch setup so the resulting traces can be compared without manual guesswork.
- Allow the debug runner to tune tracking and timing parameters for the run when that helps isolate the failure, and persist the effective values as part of the debug evidence.
- Allow the debug workflow to collect supplemental transport evidence through workspace-available tmux and terminal-recording tools, including libtmux-backed pane capture, when that is needed to explain behavior that the CAO-compatible path obscures.
- Persist all debug outputs under a repo-local `tmp/` subdirectory, including structured NDJSON event streams, inspect snapshots, pane captures, and a run summary that correlates the two paths.
- Keep the instrumentation explicitly debug-scoped so normal server and demo operation do not emit dense tracing unless the maintainer enables the debug workflow.

## Capabilities

### New Capabilities
- `houmao-server-tracking-debug`: provide a repeatable, debug-scoped instrumentation and repro workflow that explains why live server-tracked interactive lifecycle state does or does not advance for a given prompt path

### Modified Capabilities

## Impact

- `src/houmao/server/app.py`
- `src/houmao/server/service.py`
- `src/houmao/server/tui/tracking.py`
- a maintainer-facing automatic debug runner and artifact collector
- repo-local debug output under `tmp/`
- targeted verification for interactive lifecycle regressions
