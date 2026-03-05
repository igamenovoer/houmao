## Why

Headless sessions are currently inconsistent across tools: Claude/Gemini headless run as per-turn subprocess invocations while Codex uses a tool-specific long-lived `codex app-server` process that cannot be resumed from a persisted manifest after a restart. This makes automation brittle and makes it harder to debug sessions (no shared tmux contract, no unified inspectability).

We want one headless execution pattern for Claude Code, Gemini, and Codex that matches the tmux-backed contract used by TUI/CAO sessions: each agent has a tmux identity, important environment is inspectable, and multi-turn continuity is preserved via tool-native resume identifiers.

## What Changes

- Introduce a tmux-backed headless execution model for CLI agents:
  - Headless sessions create/own a tmux session (`AGENTSYS-...`) at `start-session`.
  - Each prompt turn is executed as a CLI invocation *inside that tmux session* (not a direct child `subprocess.Popen` of the runtime).
  - The runtime persists and reuses a tool-native resume identifier to maintain context across turns and across runtime restarts.
- Codex headless is implemented via resumable `codex exec` CLI turns and no longer requires `codex app-server`:
  - new session: `codex exec --json <prompt>` (or prompt via stdin)
  - resume: `codex exec --json resume <thread_id> <prompt>`
  - **BREAKING**: the default non-CAO Codex backend shifts away from `codex app-server` to resumable CLI turns.
  - `codex_app_server` SHALL remain available as an explicit opt-in backend override for one deprecation window, then be removed in a follow-up after defined stability/sunset criteria are met.
- Claude and Gemini headless keep their existing resumable CLI approach (`--resume`) but are executed inside the same tmux-backed container contract.
- Headless `stop-session` defaults to preserving the tmux session for inspectability; automation cleanup uses an explicit force-cleanup path.
- Unify tmux session contracts across CAO/TUI and headless:
  - Publish `AGENTSYS_MANIFEST_PATH=<absolute manifest path>` into the tmux session environment for all tmux-backed backends.
  - Extend name-based `--agent-identity` resolution to support tmux-backed headless sessions (not CAO-only).
- Refactor tmux helper logic so CAO and headless backends share tmux primitives and identity allocation rules while keeping launch-environment composition policy backend-specific.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `brain-launch-runtime`: add tmux-backed headless session contract; add Codex resumable CLI headless backend; de-emphasize/remove reliance on `codex app-server`.
- `agent-identity`: allow tmux name resolution for tmux-backed headless sessions (not restricted to `backend=cao_rest`).

## Impact

- Runtime backend changes under `src/agent_system_dissect/agents/brain_launch_runtime/`:
  - new/updated headless backends and shared tmux utilities
  - updated session start/resume/control wiring and identity resolution
- Session manifests stay on `session_manifest.v2` in this change and gain additive `backend_state` fields to bind headless sessions to tmux identity and resume handle.
- Operational dependency: tmux becomes required for headless Claude/Gemini/Codex sessions (matching existing CAO dependency).
