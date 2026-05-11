# Prepare Agents

Use this page when a generated execplan exists and the operator wants the required Houmao agents prepared before starting the loop.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/execplan/manifest.toml`
- generated agent bindings under `<loop-dir>/execplan/agents/`
- generated skills under `<loop-dir>/execplan/skills/`

## Procedure

1. Validate the execplan before preparing agents.
2. Read `execplan/manifest.toml`, generated participant specs, generated workspace contracts, generated agent bindings, and generated harness docs or commands to identify required concrete agents, participant roles, workdirs, skill bindings, memo or prompt sources, and dynamic lookup surfaces.
3. If agent workspaces are required, use `houmao-utils-workspace-mgr` to plan or execute workspace creation. Default to the `in-repo` flavor unless the execplan or operator explicitly selects another supported flavor.
4. Pass the workspace manager the generated agent names, launch profile names, `task-name`, and any loop bookkeeping directories requested by the execplan, such as task `runs/`, task `artifacts/`, per-agent `artifacts/`, or per-agent ignored `tmp/`.
5. Confirm the resulting workspace facts match the generated agent bindings before profile or launch work continues.
6. Register generated or private skills through maintained project-skill surfaces when project-local skill registration is needed.
7. Install each participant's generated on-event, on-tick, lifecycle, and shared harness-usage skills according to its generated agent binding.
8. Create or update specialists and profiles through `houmao-specialist-mgr` or the supported `houmao-mgr project easy` surfaces.
9. Launch missing agents through `houmao-agent-instance` or the supported easy-instance launch surface when the execplan requests live participants.
10. Prepare mailbox, gateway, memory, and inspection posture through their owning Houmao skills.
11. Confirm mail-driven loops have the mailbox posture needed for their generated schema/render communication flow.
12. Confirm generated skills can locate the plan-local harness when they depend on dynamic objective, constraint, policy, state, schema, rendering, query, validation, or controlled-apply commands.
13. Report prepared agents, workspace-manager result, missing agents, installed generated skills, harness lookup posture, mailbox posture, and any launch or binding blockers.

## Boundaries

- Do not hand-edit Houmao runtime internals.
- Do not create agent worktrees or workspace scaffolding by hand when `houmao-utils-workspace-mgr` can represent the layout.
- Do not install another participant's generated event or tick skills into the wrong agent profile.
- Do not start loop work from this page; use `start`.
- Do not invent launch profiles when the execplan or user did not provide enough information.
