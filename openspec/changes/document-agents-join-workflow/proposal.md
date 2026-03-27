## Why

The `houmao-mgr agents join` command is the simplest entry point into Houmao — it wraps an already-running CLI tool in a tmux session with Houmao's full management envelope without restarting it, requiring zero agent-definition setup. However, the project README never mentions `agents join` in any workflow section, and still claims at line 51 that "today, the management commands assume the session was launched by `houmao-mgr`" — which is outdated since `join` fulfills the bring-your-own-process design goal. There is also no demo pack that exercises the join workflow end-to-end, making it hard for new users to verify their understanding or for CI to validate the path.

## What Changes

- Add a new "Quick Start: Adopt an Existing Session" section to `README.md` before the current "Basic Workflow" section, showing the TUI join, join-with-relaunch-options, and headless join workflows with Mermaid sequence diagrams explaining how join wraps an existing process.
- Update the outdated "How Agents Join Your Workflow" paragraph in `README.md` to reflect that `agents join` is a working, first-class adoption path rather than a future design goal.
- Add a new demo pack at `scripts/demo/agents-join-demo-pack/` that exercises the TUI join lifecycle end-to-end: start a provider in tmux, join it, inspect state, submit a prompt, and stop — following the established demo pack conventions used by other packs in `scripts/demo/`.
- Add a README to the demo pack documenting prerequisites, quick start, step-by-step walkthrough, and expected outputs.

## Capabilities

### New Capabilities

- `agents-join-demo-pack`: a demo script pack under `scripts/demo/agents-join-demo-pack/` that exercises the `houmao-mgr agents join` TUI adoption lifecycle end-to-end, including provider startup in tmux, join, state inspection, prompt submission, and stop.

### Modified Capabilities

- `docs-getting-started`: add a "Quick Start: Adopt an Existing Session" section to `README.md` showing the join workflow with Mermaid diagrams, and fix the outdated "How Agents Join Your Workflow" paragraph.

## Impact

- Affected files: `README.md`, new files under `scripts/demo/agents-join-demo-pack/`.
- No code changes to `src/houmao/` — this is purely documentation and demo scripting.
- No breaking changes.
- Depends on existing `houmao-mgr agents join`, `agents state`, `agents prompt`, `agents stop` commands working as currently implemented.
