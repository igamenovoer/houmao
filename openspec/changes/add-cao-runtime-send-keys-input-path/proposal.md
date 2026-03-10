## Why

The runtime currently exposes CAO-backed prompt submission as a high-level "send text and complete a turn" path, but it does not expose a lower-level input path for live TUI interaction. That makes it impossible to drive slash-command menus, selection prompts, or partial typed input that must not auto-submit with `Enter`.

## What Changes

- Add a new `send-keys` runtime/CLI control-input path for tmux-backed CAO sessions that injects a raw key stream into the live terminal without automatically pressing `Enter`.
- Name the internal runtime/backend mixed-input method `send_input_ex()` so it reads as the advanced version of the existing CAO `send_input()` path without overloading `send-prompt`.
- Return a single control-action result for `send-keys` by extending the existing `SessionControlResult` shape with `action="control_input"` rather than inventing a new turn-result family.
- Keep the existing CAO-backed `send-prompt` behavior unchanged as the high-level prompt-turn submission path.
- Define a mixed input grammar where literal text can be combined with tmux control-key tokens written as exact `<[key-name]>` substrings.
- Add a global escape mode that disables special-key parsing and sends the provided string literally, even when it contains `<[...]>` sequences.
- Resolve tmux targets from persisted runtime session state and live CAO terminal metadata so callers can continue addressing sessions by `agent_identity` rather than raw tmux window names, persisting optional `tmux_window_name` metadata in CAO manifests for fast reuse.
- Define explicit errors for unsupported backends, unresolved tmux targets, invalid or unsupported key tokens, and malformed mixed-input strings.

## Capabilities

### New Capabilities

- `runtime-tmux-control-input`: Defines the raw tmux-backed control-input grammar, delivery semantics, escaping behavior, and supported mixed text/control-key stream behavior for managed runtime sessions.

### Modified Capabilities

- `brain-launch-runtime`: Extend the runtime CLI and session-control contract so callers can use a manifest-driven `send-keys` style command backed by `send_input_ex()` for tmux-backed CAO sessions while preserving the existing `send-prompt` path unchanged.

## Impact

- Affected code: `src/gig_agents/agents/brain_launch_runtime/cli.py`, `src/gig_agents/agents/brain_launch_runtime/runtime.py`, `src/gig_agents/agents/brain_launch_runtime/models.py`, `src/gig_agents/agents/brain_launch_runtime/backends/cao_rest.py`, `src/gig_agents/agents/brain_launch_runtime/backends/tmux_runtime.py`, and session-manifest boundary/schema helpers under `src/gig_agents/agents/brain_launch_runtime/`.
- Affected tests: runtime CLI tests, CAO backend unit/integration tests, session-manifest validation tests, and the existing `scripts/demo/cao-claude-esc-interrupt/` flow.
- Affected docs/specs: runtime CLI/session-control docs and OpenSpec requirements for runtime session control and the new tmux control-input contract.
- Dependencies: no new external dependency is required; the change relies on the existing tmux-backed CAO/runtime environment.
