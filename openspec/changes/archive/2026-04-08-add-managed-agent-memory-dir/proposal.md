## Why

Houmao currently distinguishes between durable runtime-owned session state and scratch `job_dir`, but it does not provide a supported durable memory location for an agent to keep source materials, working notes, downloaded artifacts, or extracted knowledge across launches. That gap pushes users and agents toward ad hoc filesystem choices with no manifest-backed discovery path and no consistent lifecycle semantics.

## What Changes

- Add an optional managed-agent memory-dir contract for tmux-backed managed sessions.
- Define a conservative project-local default when memory is enabled: `<active-overlay>/memory/agents/<agent-id>/`.
- Allow operators to disable memory-dir creation for a launch or profile with an explicit no-memory option.
- Allow operators to point one launch or profile at an exact external memory directory, including intentionally shared directories used by multiple agents.
- Persist the resolved memory-dir result in runtime-backed session state and publish it to the running agent environment for manifest-first discovery.
- Expose the resolved memory-dir through supported `houmao-mgr` inspection surfaces.
- Treat memory directories as operator or agent-owned durable state rather than cleanup-owned scratch.

## Capabilities

### New Capabilities
- `agent-memory-dir`: Optional durable per-agent memory-directory semantics, including conservative default placement, explicit disable, exact external-path binding, runtime manifest and env publication, inspection visibility, and cleanup non-ownership.

### Modified Capabilities
- `agent-launch-profiles`: Launch profiles gain reusable memory-dir defaults and precedence rules.
- `brain-launch-runtime`: Runtime launch and join flows resolve, persist, and publish memory-dir state for managed sessions.
- `houmao-mgr-agents-launch`: `agents launch` accepts one-off memory-dir controls and applies them over profile defaults.
- `houmao-mgr-agents-join`: `agents join` accepts one-off memory-dir controls and persists the adopted session's memory binding.
- `houmao-mgr-project-agents-launch-profiles`: Explicit recipe-backed launch-profile CRUD supports stored memory-dir defaults.
- `houmao-mgr-project-easy-cli`: Easy profile authoring, easy instance launch, and easy instance inspection support memory-dir defaults and resolved memory-dir reporting.

## Impact

- Affected code includes project launch-profile storage and projection, runtime launch or join materialization, session manifest and state reporting, and `houmao-mgr` launch-profile and easy CLI surfaces.
- Affected runtime contract includes a new managed session environment variable and new manifest-backed durable metadata for optional memory-dir state.
- Cleanup behavior changes only in ownership rules: memory directories remain durable and are not treated as session scratch like `job_dir`.
