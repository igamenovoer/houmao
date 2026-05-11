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
2. Read `execplan/manifest.toml`, generated participant specs, generated agent bindings, and generated harness docs or commands to identify required concrete agents, participant roles, workdirs, skill bindings, memo or prompt sources, and dynamic lookup surfaces.
3. Register generated or private skills through maintained project-skill surfaces when project-local skill registration is needed.
4. Install each participant's generated on-event, on-tick, lifecycle, and shared harness-usage skills according to its generated agent binding.
5. Create or update specialists and profiles through `houmao-specialist-mgr` or the supported `houmao-mgr project easy` surfaces.
6. Launch missing agents through `houmao-agent-instance` or the supported easy-instance launch surface when the execplan requests live participants.
7. Prepare mailbox, gateway, memory, and inspection posture through their owning Houmao skills.
8. Confirm mail-driven loops have the mailbox posture needed for their generated schema/render communication flow.
9. Confirm generated skills can locate the plan-local harness when they depend on dynamic objective, constraint, policy, state, schema, rendering, query, validation, or controlled-apply commands.
10. Report prepared agents, missing agents, installed generated skills, harness lookup posture, mailbox posture, and any launch or binding blockers.

## Boundaries

- Do not hand-edit Houmao runtime internals.
- Do not install another participant's generated event or tick skills into the wrong agent profile.
- Do not start loop work from this page; use `start`.
- Do not invent launch profiles when the execplan or user did not provide enough information.
