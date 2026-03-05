## Why

Our brain-launch runtime currently requires users to address running agents by a session manifest JSON path (for example `--session-manifest tmp/.../session.json`). This is inconvenient for humans and makes it harder to operate multiple concurrent agents. Additionally, tmux sessions created for tmux-backed agents are not named in a human-meaningful way.

## What Changes

- Add `--agent-identity <name|manifest-path>` to session control commands (prompt/stop) so users can target an agent by a short human name or by an explicit manifest path.
- **BREAKING**: Remove `--session-manifest <manifest-path>` in favor of `--agent-identity`.
- Introduce a canonical tmux session naming scheme for tmux-backed agents:
  - User-provided names map to `AGENTSYS-<name>` (auto-prefix when omitted).
  - The exact string `AGENTSYS` is reserved and cannot be used as an agent name.
  - If no name is provided at start, the system auto-generates a short, easy-to-type name derived from the agent profile (tool + role/blueprint) with a conflict-avoiding suffix.
- For tmux-backed agents, embed the session manifest path into the tmux session environment as `AGENTSYS_MANIFEST_PATH` so name resolution does not depend on a shared runtime root layout.

## Capabilities

### New Capabilities
- `agent-identity`: Human-friendly agent identities (name normalization, `AGENTSYS-` namespace conventions, and tmux-backed resolution via `AGENTSYS_MANIFEST_PATH`).

### Modified Capabilities
- `brain-launch-runtime`: Replace session-manifest-only CLI addressing with `--agent-identity`, and require tmux-backed sessions to use canonical `AGENTSYS-...` session names with a manifest-path tmux env pointer.

## Impact

- Runtime CLI surface:
  - `src/agent_system_dissect/agents/brain_launch_runtime/cli.py`
- CAO/tmux-backed runtime session launch and resolution:
  - `src/agent_system_dissect/agents/brain_launch_runtime/backends/cao_rest.py`
  - `src/agent_system_dissect/agents/brain_launch_runtime/runtime.py`
- Demos and docs that currently pass `--session-manifest`:
  - `scripts/demo/**`
- Tests for new identity parsing and tmux env pointer behavior:
  - `tests/unit/agents/brain_launch_runtime/`
