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
2. Read generated agent bindings to identify required concrete agents, participant roles, workdirs, skill bindings, and memo or prompt sources.
3. Register generated or private skills through maintained project-skill surfaces when project-local skill registration is needed.
4. Create or update specialists and profiles through `houmao-specialist-mgr` or the supported `houmao-mgr project easy` surfaces.
5. Launch missing agents through `houmao-agent-instance` or the supported easy-instance launch surface when the execplan requests live participants.
6. Prepare mailbox, gateway, memory, and inspection posture through their owning Houmao skills.
7. Report prepared agents, missing agents, and any launch or binding blockers.

## Boundaries

- Do not hand-edit Houmao runtime internals.
- Do not install another participant's generated event skills into the wrong agent profile.
- Do not start loop work from this page; use `start`.
- Do not invent launch profiles when the execplan or user did not provide enough information.
