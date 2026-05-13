## Why

The current loop skill treats workspace preparation as part of agent preparation, even though workspace setup has independent Git, filesystem, launch-cwd, knowledge-directory, and bookkeeping consequences. Separating workspace preparation into its own ordered execution stage makes generated loops easier to review, approve, run, and recover without letting `prepare-agents` implicitly create or repair workspaces.

## What Changes

- Add a `prepare-workspace` execution subcommand to the loop skill.
- Keep `prepare-workspace` and `prepare-agents` as separate operator-invoked stages:
  - `prepare-workspace` prepares or verifies multi-agent workspaces from generated workspace contracts;
  - `prepare-agents` prepares profiles, generated skill bindings, maintained mail support, mailbox/gateway posture, memo posture, and optional live agents.
- Require `prepare-workspace` to route supported workspace planning and execution through `houmao-utils-workspace-mgr`.
- Require generated workspace contracts to provide enough inputs for workspace-manager planning and execution, including workspace flavor, task name, agent/profile mapping, launch cwd policy, work roots, knowledge paths, shared resources, and loop bookkeeping directories.
- Require postcondition checks that prepared workspace facts match generated agent bindings before later execution stages proceed.
- Revise `prepare-agents` so it verifies workspace readiness when required, but does not call, route to, create, or repair workspace setup.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-agent-loop-pairwise-v5-skill`: Execution behavior changes to add an independent `prepare-workspace` stage, tighten workspace contract generation/validation, and make `prepare-agents` depend on workspace readiness without invoking workspace preparation.

## Impact

- Affected skill assets: `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v5/`.
- Affected execution routing: add `prepare-workspace`; keep `prepare-agents` as a separate stage.
- Affected authoring guidance: generated workspace specs and agent bindings must contain enough structured information for workspace-manager input.
- Affected validation guidance: execplan validation must check workspace-manager routing, workspace readiness postconditions, and stage separation.
- Affected platform boundary guidance: workspace creation remains delegated to `houmao-utils-workspace-mgr`; the loop skill only adapts generated contracts into that maintained workspace surface.
