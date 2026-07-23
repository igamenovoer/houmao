## Why

Houmao can create specialists and profiles, but operators must currently assemble each task-specific agent from low-level pieces. A portable agent blueprint format and a guided deployment workflow will let Houmao reuse predefined agent intent while adapting only declared task-specific inputs into complete, inspectable project definitions.

## What Changes

- Add a versioned agent blueprint package contract for built-in and operator-supplied local definitions.
- Add strict, non-executable placeholder rendering that separates fixed agent behavior from typed task-specific inputs.
- Add project commands to list and inspect blueprints, plan a deployment without durable mutation, apply the plan atomically, inspect and diagnose deployed definitions, and safely remove deployment-owned resources.
- Persist deployment ownership, blueprint provenance, and rendered-content digests in the project catalog while keeping generated content file-backed.
- Extend the protected `houmao-agent-definition` routines with an admin-only `deploy-blueprint` subcommand that converts a user task into typed blueprint inputs, previews the deterministic plan, applies an authorized deployment, and returns the normal profile launch command without launching the agent.
- Route human-operator blueprint requests implicitly through `houmao-admin-entrypoint`, while retaining an explicit advanced route through `houmao-shared-routines` and preventing managed-agent self-administration.
- Package initial built-in blueprints with Houmao and document how operators author local blueprints and deploy the resulting individual agents.

## Capabilities

### New Capabilities

- `agent-blueprint-packages`: Defines the portable blueprint directory, manifest, typed inputs, static templates, skill material, source resolution, validation, and safe rendering contract.
- `houmao-mgr-agent-blueprint-deployments`: Defines project CLI and service behavior for blueprint discovery, planning, atomic application, provenance, inspection, drift diagnosis, update protection, and removal.

### Modified Capabilities

- `houmao-manage-agent-definition-skill`: Adds the admin-only `deploy-blueprint` subcommand and its task interpretation, preview, apply, validation, and launch-handoff workflow.
- `houmao-admin-entrypoint-skill`: Routes human-operator blueprint deployment intent through the protected agent-definition routine.
- `houmao-shared-routines-skill`: Exposes the blueprint deployment routine for explicit advanced invocation while preserving actor restrictions.
- `project-config-catalog`: Adds canonical deployment records and managed rendered-content ownership to project overlays.
- `docs-stale-content-removal`: Distinguishes the new agent blueprint package term from the retired native-agent `blueprints/` layout.

## Impact

The change affects packaged agent assets, project catalog schema and content layout, `houmao-mgr project` commands, agent-definition system-skill routing, built-in package data, tests, and operator/developer documentation. It reuses the existing specialist, profile, private-skill, credential-selection, and managed-agent launch surfaces; it does not change runtime launch composition or automatically launch a deployed agent.
