## Why

Agent Definition authoring workspaces contain source intent, operator interpretation, validation evidence, and an optional immutable revision, but they do not explain themselves at the directory root. A user receiving one of these workspaces must reconstruct its purpose, lifecycle state, file roles, and continuation path from Houmao internals.

## What Changes

- Require the agent-definition authoring route to generate `<authoring-dir>/README.md` when it initializes or resumes an authoring workspace.
- Require the route to refresh that README before every user-facing authoring stop or handoff so it describes the files and lifecycle state that actually exist.
- Define a portable README contract covering purpose, lifecycle state, directory tree, exhaustive file inventory, ownership and authority, immutable revision identity, continuation commands, and distribution guidance.
- Keep the README non-authoritative and outside source, derived, approval, instance-contract, and immutable-revision digests.
- Prefer the workspace-local `agent-definition/` output when the user does not explicitly request an external revision path.
- Add a README to the maintained `swe-critic` authoring example and update behavior qualification for manual and automatic authoring routes.

## Capabilities

### New Capabilities

- `agent-definition-authoring-readme`: Defines the generated authoring-root README, its required contents, refresh boundaries, portability rules, and non-authoritative status.

### Modified Capabilities

- `houmao-manage-agent-definition-skill`: Requires the packaged authoring route to create and refresh the authoring README while preserving existing review and materialization boundaries.

## Impact

The change affects the packaged `houmao-agent-definition` subskill, agent-definition authoring documentation, the `swe-critic` example workspace, system-skill tests, and behavior qualification cases. It does not change `houmao-mgr` commands, the authoring directory schema, materialization inputs, immutable revision schema, deployment behavior, or runtime dependencies.
