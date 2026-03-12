## Why

Tmux-backed runtime control commands such as `stop-session` currently require callers to provide `--agent-def-dir` even when the addressed agent session is already live and discoverable by name. That makes single-agent termination and other name-based control flows more coupled and cwd-dependent than they need to be, despite the runtime already publishing session metadata into tmux environment state.

## What Changes

- **BREAKING**: Change name-based tmux-backed runtime control so omitted `--agent-def-dir` no longer forces resolution through the caller environment or cwd defaults first.
- Publish `AGENTSYS_AGENT_DEF_DIR=<absolute agents dir>` into tmux session environment for tmux-backed headless and CAO-backed launches alongside `AGENTSYS_MANIFEST_PATH`.
- Update name-based session-control commands (`send-prompt`, `send-keys`, `stop-session`) to recover the effective agent-definition root from the addressed tmux session when `--agent-def-dir` is omitted.
- Update in-repo name-based operator flows such as the interactive demo wrappers to omit explicit `--agent-def-dir` for `send-prompt`, `send-keys`, and `stop-session` so they use the new tmux-session-derived default instead of bypassing it.
- Keep explicit `--agent-def-dir` as the highest-precedence override for session-control commands.
- Fail explicitly when tmux-backed name resolution finds a missing, blank, non-absolute, or stale `AGENTSYS_AGENT_DEF_DIR` pointer instead of silently falling back to an unrelated cwd-derived agents tree.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime`: tmux-backed launches and name-addressed session-control requirements change so runtime control can recover the session's agent-definition root from tmux environment state.
- `agent-identity`: tmux-backed session environment requirements change to publish and validate `AGENTSYS_AGENT_DEF_DIR` in addition to `AGENTSYS_MANIFEST_PATH` during name-based resolution.
- `cao-interactive-demo-operator-workflow`: the interactive demo's prompt/control/stop flows change to rely on the runtime's tmux-session-derived default for name-addressed control instead of always passing explicit `--agent-def-dir`.

## Impact

- Affected code: `src/gig_agents/agents/brain_launch_runtime/cli.py`, `src/gig_agents/agents/brain_launch_runtime/runtime.py`, `src/gig_agents/agents/brain_launch_runtime/backends/headless_base.py`, `src/gig_agents/agents/brain_launch_runtime/backends/cao_rest.py`, `src/gig_agents/demo/cao_interactive_demo/commands.py`, `src/gig_agents/demo/cao_interactive_demo/runtime.py`, and related resolution/session-control models.
- Affected tests: runtime CLI unit/integration coverage for `send-prompt`, `send-keys`, and `stop-session` with omitted `--agent-def-dir` plus tmux-env validation failures.
- Affected docs: runtime CLI/reference docs and interactive demo/operator guidance that currently says or implies session-control always needs explicit `--agent-def-dir`.
