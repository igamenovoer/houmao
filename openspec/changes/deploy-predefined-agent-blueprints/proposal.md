## Why

Houmao can persist specialists and project profiles, but it has no lifecycle for turning a human-authored individual-agent concept into a portable reusable definition and then a concrete project deployment. The system needs a small foundation that preserves freeform source intent, records the operator agent's interpretation, materializes an immutable definition revision, and resolves task-specific inputs only during deployment.

This change is the foundation of a change series. Batch deployment, managed-agent instance state, and optional private workspaces are specified by dependent changes so that each part can be implemented and validated independently.

## What Changes

- Add an Agent Definition Workspace with one required freeform source entrypoint at `intent/src/agent-def-overview.md`.
- Keep operator interpretation under `intent/derived/` without rewriting human-owned source intent.
- Reduce the derived contract to `interpretation.md`, `materialization.toml`, copied `materials/`, `validation.json`, and `approval.toml`.
- Materialize an immutable, portable Agent Definition Revision containing `definition.toml`, `deploy-contract.toml`, `instance-contract.toml`, assets, and provenance.
- Define typed deployment inputs and context-safe target bindings in `deploy-contract.toml`. V1 does not claim deterministic validation of freeform semantic rewrites.
- Split operator-authored deployment input from deterministic output by introducing a Deployment Request and Deployment Plan.
- Apply one plan as one project Agent Deployment that owns its generated project profile, specialist relationship, registered skills, content digests, and provenance.
- Keep deployment separate from managed-agent launch and return the maintained launch command after apply.
- Fold `init-intent`, derive, approve, materialize, plan, apply, inspect, doctor, update, and remove into the existing `houmao-agent-definition` shared routine. Do not add a competing authoring routine.
- Block deployment updates that change the instance-contract digest while a live or preserved managed-agent instance references that deployment.
- Route human authoring and deployment through `houmao-admin-entrypoint`, while retaining explicit advanced invocation through public `houmao-shared-routines`.
- Retain UC-01 and UC-02 here. Move plural deployment, runtime variables, mindsets, and private workspaces into dependent OpenSpec changes.

## Capabilities

### New Capabilities

- `agent-definition-authoring-workspaces`: Defines the source, derived interpretation, approval, and materialization boundary.
- `agent-definition-bundles`: Defines portable immutable Agent Definition Revisions and their deploy and instance contracts.
- `houmao-mgr-agent-definition-deployments`: Defines definition discovery, materialization, Deployment Requests, deterministic Deployment Plans, project apply, doctor, update, and removal.

### Modified Capabilities

- `houmao-manage-agent-definition-skill`: Adds authoring and deployment subcommands to the existing routine.
- `houmao-admin-entrypoint-skill`: Routes human Agent Definition authoring and deployment without conflating deployment with launch.
- `houmao-shared-routines-skill`: Exposes the existing Agent Definition routine for explicit advanced invocation under admin posture.
- `project-config-catalog`: Stores canonical Agent Deployment ownership and provenance.
- `docs-stale-content-removal`: Documents Agent Definitions without reviving the retired native-agent blueprint layout.

## Impact

The change affects packaged definition assets, Agent Definition CLI commands, the existing Agent Definition shared routine, admin routing, project catalog schema and managed content, generated skill prompts, tests, and documentation. Existing specialist, profile, registered-skill, credential-reference, and managed-agent launch surfaces remain the concrete project and runtime boundaries.
