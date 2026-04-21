## Why

Operators currently have to choose between relaunch semantics that preserve the already-built managed home and fresh launch semantics that rebuild from current profile or specialist state. There is no supported lifecycle surface for "refresh Houmao-managed launch material, but keep the existing runtime home", so provider-local chat history becomes difficult to recover after ordinary stop and relaunch workflows.

## What Changes

- Add an explicit launch-owned reused-home mode to `houmao-mgr agents launch` so a fresh managed launch can rebuild current launch inputs onto one compatible existing runtime home.
- Add the same explicit reused-home mode to `houmao-mgr project easy instance launch` and forward it through the delegated managed launch flow.
- Define runtime behavior for reused-home launch: preserve provider-owned history and caches that live outside Houmao-managed projection targets, refresh current Houmao-managed setup/auth/skills/config/env/launch-helper material, and create new live session authority for the new launch.
- Keep reused-home launch distinct from relaunch and stopped-session revival. Reused-home launch does not consume relaunch chat-session policy, does not silently fall back to a brand-new home when no compatible preserved home exists, and does not allow destructive clean-home semantics that would discard the preserved provider history.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime`: add runtime semantics for fresh managed launch that rebuilds onto one compatible preserved home while staying distinct from relaunch and stopped-session revival.
- `houmao-mgr-agents-launch`: add an explicit `agents launch` surface for reuse-home fresh launch against one compatible existing managed home.
- `houmao-mgr-project-easy-cli`: add the corresponding easy-instance launch surface for reuse-home fresh launch through specialist-backed and easy-profile-backed launch paths.

## Impact

- Affected code: `src/houmao/srv_ctrl/commands/agents/core.py`, `src/houmao/srv_ctrl/commands/project_easy.py`, `src/houmao/srv_ctrl/commands/managed_agents.py`, `src/houmao/agents/brain_builder.py`, and related runtime helpers.
- Affected tests: managed launch CLI tests, easy launch CLI tests, runtime registry/relaunch tests, and builder reuse-home coverage.
- Affected docs: launch lifecycle and launch-profile guidance for the new explicit reuse-home mode and its distinction from relaunch.
