## Why

The runtime currently separates canonical agent identity (`AGENTSYS-<name>`) from the live tmux session handle and uses opaque runtime-owned tmux names such as `houmao-...`. That makes tmux sessions harder for operators to recognize, and it keeps some control and demo flows tied to a legacy assumption that canonical agent identity and tmux handle are interchangeable.

## What Changes

- Change tmux-backed runtime session naming for the current tmux-backed backend set (`codex_headless`, `claude_headless`, `gemini_headless`, and `cao_rest`) so live tmux sessions use the format `<canonical-agent-name>-<agent-id-prefix>` instead of opaque `houmao-...` names.
- Define the default tmux naming suffix length as the first 6 characters of the authoritative `agent_id`, while preserving room for collision handling when a 6-character prefix is not unique.
- Update tmux-backed name resolution so canonical `AGENTSYS-<name>` addressing remains stable even when the live tmux session handle includes an agent-id suffix.
- **BREAKING**: operators, scripts, and docs that directly attach or inspect tmux by assuming the live session name is exactly `AGENTSYS-<name>` must move to the new tmux handle contract or use persisted runtime metadata to discover the handle.
- Update interactive demo operator workflows and surfaced inspection output so they show the actual tmux handle instead of assuming it matches the canonical agent identity.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-identity`: tmux-backed sessions now use deterministic agent-id-suffixed tmux session handles, and name-based control must resolve canonical agent identities without requiring the tmux handle to equal the canonical name.
- `cao-interactive-demo-inspect-surface`: the interactive demo inspect surface must expose the actual tmux handle and attach command when that handle differs from the canonical agent identity.
- `cao-interactive-demo-startup-recovery`: demo startup cleanup must reset stale tmux-backed sessions associated with the canonical tutorial identity even when the live tmux handle includes an agent-id suffix.

## Impact

- Affected code: `src/houmao/agents/realm_controller/agent_identity.py`, `src/houmao/agents/realm_controller/runtime.py`, `src/houmao/agents/realm_controller/manifest.py`, tmux backend helpers, CAO/headless backend constructors, and interactive demo lifecycle code.
- Affected behavior: tmux session creation for the current tmux-backed backend set, tmux-local identity resolution, manifest persistence defaults, shared-registry terminal metadata, and operator-visible attach/inspection guidance.
- Affected docs/tests: runtime reference docs, CAO troubleshooting/demo docs, and tests that currently assume `agent_name == tmux_session_name` or `tmux attach -t AGENTSYS-...`.
