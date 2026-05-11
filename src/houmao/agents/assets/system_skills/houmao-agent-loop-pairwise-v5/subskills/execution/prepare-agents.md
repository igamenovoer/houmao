# Prepare Agents

## Preconditions

- Generated execplan exists.
- Operator wants required Houmao agents prepared before starting the loop.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/execplan/manifest.toml`
- generated agent bindings under `<loop-dir>/execplan/agents/`
- generated skills under `<loop-dir>/execplan/skills/`

## Actions

1. Validate the execplan before preparing agents.
2. Read `execplan/manifest.toml`, generated participant specs, generated workspace contracts, generated agent bindings, and generated harness docs or commands to identify required concrete agents, participant roles, workdirs, skill bindings, memo or prompt sources, and dynamic lookup surfaces.
3. If agent workspaces are required, use `houmao-utils-workspace-mgr` to plan or execute workspace creation. Default to the `in-repo` flavor unless the execplan or operator explicitly selects another supported flavor.
4. Pass the workspace manager the generated agent names, launch profile names, `task-name`, and any loop bookkeeping directories requested by the execplan, such as task `runs/`, task `artifacts/`, per-agent `artifacts/`, or per-agent ignored `tmp/`.
5. Confirm the resulting workspace facts match the generated agent bindings before profile or launch work continues.
6. Register generated or private skills through maintained project-skill surfaces when project-local skill registration is needed.
7. Install each participant's generated on-event, on-tick, lifecycle, and shared harness-usage skills according to its generated agent binding.
8. For mail-driven participants, bind the maintained mail support skills required by the generated agent binding. Use `houmao-agent-email-comms` for ordinary mail operations, `houmao-process-emails-via-gateway` for notifier-driven open-mail rounds, `houmao-mailbox-mgr` for mailbox administration, `houmao-agent-messaging` for managed-agent communication routing, and `houmao-agent-gateway` for gateway posture.
9. Create or update specialists and profiles through `houmao-specialist-mgr` or the supported `houmao-mgr project easy` surfaces.
10. Launch missing agents through `houmao-agent-instance` or the supported easy-instance launch surface when the execplan requests live participants.
11. Prepare mailbox, gateway, memory, and inspection posture through their owning Houmao skills.
12. Confirm mail-driven loops have the mailbox posture needed for their generated schema/render communication flow, including notifier posture when generated mail-received skills expect gateway-notified rounds.
13. Confirm generated skills can locate the plan-local harness when they depend on dynamic objective, constraint, policy, state, schema, rendering, query, validation, or controlled-apply commands.
14. Report prepared agents, workspace-manager result, missing agents, installed generated skills, maintained mail support bindings, harness lookup posture, mailbox and gateway posture, and any launch or binding blockers.

## Constraints

- Do not hand-edit Houmao runtime internals.
- Do not create agent worktrees or workspace scaffolding by hand when `houmao-utils-workspace-mgr` can represent the layout.
- Do not install another participant's generated event or tick skills into the wrong agent profile.
- Do not duplicate mailbox endpoint contracts, mailbox storage, gateway discovery, or ordinary mail send/read/reply/archive mechanics inside generated agent preparation.
- Do not start loop work from this page; use `start`.
- Do not invent launch profiles when the execplan or user did not provide enough information.
