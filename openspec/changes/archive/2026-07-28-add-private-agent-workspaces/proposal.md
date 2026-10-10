## Why

Some individual agents need private, instance-owned storage inside the user project, while most should continue working directly from the project root. Houmao needs a standard semantic path contract and workspace manifest so definition authors do not need a custom harness.

This change depends on `deploy-predefined-agent-blueprints` and `add-managed-agent-instance-state`.

## What Changes

- Extend Agent Definition instance contracts with an optional Private Agent Workspace Contract.
- Keep `execution_workdir` and `private_state_root` independent. Enabling private storage does not change the process workdir unless the definition explicitly selects `private-root`.
- Create one project-contained private workspace per managed-agent instance during launch.
- Store stable identity, topology, semantic path bindings, tracking posture, index filename, and index schema in `houmao-agent-workspace.toml`.
- Store mutable generations and growing record metadata in `houmao-agent-workspace.sqlite`. Do not place a mutable database digest or generation in TOML.
- Use stable semantic labels with adjustable confined relative paths.
- Keep the workspace locally untracked through owned repository-local Git exclude state by default, with explicit human opt-in for tracking.
- Provide explicit-target admin mutation and verified-self read-only path resolution.
- Permit immutable mindset projections into the private workspace while keeping the canonical mindset record in instance state.
- Prepare the workspace through an idempotent launch state machine and preserve failed-attempt evidence rather than claiming cross-filesystem atomicity.

## Capabilities

### New Capabilities

- `houmao-agent-private-workspaces`: Defines reusable contracts, per-instance TOML topology, SQLite indexes, semantic paths, Git posture, lifecycle, and cleanup.

### Modified Capabilities

- `agent-definition-bundles`: Adds the optional private-workspace contract and independent workdir policy to the instance contract.
- `houmao-mgr-agent-definition-deployments`: Preserves workspace policy without creating instance content.
- `houmao-agent-mindsets`: Adds optional immutable workspace projections without moving record authority.
- `houmao-admin-entrypoint-skill`: Routes explicit-instance workspace operations.
- `houmao-agent-entrypoint-skill`: Routes verified-self semantic path reads.
- `houmao-shared-routines-skill`: Exposes actor-scoped workspace operations through the existing agent-instance routine.

## Impact

The change affects managed launch, agent-instance state, project-local workspace storage, Git exclude management, definition validation, agent-instance CLI commands, system-skill routing, tests, and documentation. It does not replace standard multi-agent worktrees or provide OS-level isolation.
