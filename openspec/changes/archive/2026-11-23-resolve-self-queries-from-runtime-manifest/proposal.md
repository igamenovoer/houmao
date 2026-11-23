# Proposal

## Why

Kimi Web and DSH Web self queries failed after Houmao found their valid runtime manifests. The CLI rebuilt a controller and tried to read the launch-time agent definition directory before it could return identity or route mailbox work.

## What Changes

- Resolve `agents self identity` from the verified session manifest. Use the owning tmux session or the supported runtime-owned locator to find it and validate it against the current registry generation.
- Publish any missing agent metadata and observation bindings to the manifest at launch, join, or relaunch. Self queries obtain agent details from that record. Commands that report current state use the runtime sources named by the manifest.
- Use the same verified manifest for self gateway and mailbox routing. The notifier round can check identity, access its bound mailbox, reply, and archive with the definition directory unavailable.
- Treat the agent definition directory as a launch and relaunch input. Inspecting or addressing an already-running agent uses its committed runtime artifacts.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime` publishes the metadata and authority used by managed runtime readers and reserves definition-directory access for launch planning.
- `houmao-managed-agent-self-identity` uses verified manifest fields for self identity with existing ownership and generation validation.
- `houmao-mgr-agents-scope-cli` gives self inspection and mailbox commands a verified manifest-based target.
- `houmao-srv-ctrl-native-cli` resolves self gateway and status commands without loading launch definitions.

## Impact

The change affects session manifest publication, the current-session resolver, controller reconstruction, and the local self CLI paths for state, gateway, and mailbox work. Verification covers both Web backends and representative TUI, headless, and service paths using their supported self context.
