## Why

Mailbox enablement is currently treated as launch-time session state, which forces operators to decide mailbox bindings before `houmao-mgr agents launch` or `houmao-mgr agents join`. For local serverless workflows, that is the wrong seam: operators need to bootstrap and manage a filesystem mailbox root separately, then register or unregister an existing managed agent against that mailbox after the session already exists.

## What Changes

- Add a local `houmao-mgr mailbox ...` command family for filesystem mailbox root administration without `houmao-server`.
- Add a local `houmao-mgr agents mailbox status|register|unregister ...` command family for attaching and removing mailbox bindings on existing managed agents after launch or join.
- Persist late mailbox registration into the managed session manifest and shared-registry visibility so later `houmao-mgr agents mail ...` commands can reuse the registered binding.
- Define activation behavior for late mailbox registration, including immediate activation for local headless sessions, relaunch-required activation for long-lived local interactive sessions, and explicit rejection for joined sessions that cannot be relaunched safely.
- Keep `houmao-mgr agents launch` and `houmao-mgr agents join` mailbox-agnostic; mailbox setup moves to the later registration workflow instead of new launch flags.

## Capabilities

### New Capabilities
- `houmao-mgr-mailbox-cli`: local operator commands for initializing, inspecting, repairing, and explicitly managing filesystem mailbox roots without a server.
- `managed-agent-mailbox-registration`: late mailbox registration and unregistration for existing local managed-agent sessions, including manifest persistence, registry visibility, and activation-state reporting.

### Modified Capabilities
- `houmao-srv-ctrl-native-cli`: extend the native `houmao-mgr` command tree with the new top-level `mailbox` group and the `agents mailbox` subfamily for local mailbox registration workflows.

## Impact

- Affected code:
  `src/houmao/srv_ctrl/commands/main.py`, new `src/houmao/srv_ctrl/commands/mailbox.py`, `src/houmao/srv_ctrl/commands/agents/core.py`, `src/houmao/srv_ctrl/commands/managed_agents.py`, `src/houmao/agents/realm_controller/runtime.py`, and mailbox support helpers under `src/houmao/mailbox/`.
- Affected operator surfaces:
  `houmao-mgr --help`, new `houmao-mgr mailbox ...`, and new `houmao-mgr agents mailbox ...`.
- Affected persisted state:
  session manifests and shared-registry mailbox summaries for local managed agents.
- Dependencies and systems:
  filesystem mailbox bootstrap and registration lifecycle, local tmux-backed runtime relaunch rules, and local managed-agent discovery.
