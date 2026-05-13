# Prepare Agents

## Read First

- `../reference/generated-contract-defaults.md`
- MUST READ: `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`

## Preconditions

- Generated execplan exists.
- Workspace readiness has been prepared or verified when the execplan requires managed workspaces.
- Operator wants required Houmao agents prepared before starting the loop.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/execplan/manifest.toml`
- generated agent bindings under `<loop-dir>/execplan/agents/`
- generated skills under `<loop-dir>/execplan/skills/`
- generated workspace contracts and workspace readiness facts when the execplan requires managed workspaces

## Actions

1. Validate the execplan before preparing agents.
2. Read `execplan/manifest.toml`, generated participant specs, generated workspace contracts, generated agent bindings, generated run artifact contracts, and generated harness docs or commands to identify required concrete agents, participant roles, workdirs, skill bindings, memo or prompt sources, dynamic lookup surfaces, and run artifact paths.
3. If managed workspaces are required, verify readiness facts from `prepare-workspace` or existing workspace contract docs:
   - required workspace docs exist;
   - required agent work roots and knowledge paths exist;
   - required shared resources and loop bookkeeping directories exist;
   - launch cwd posture matches the generated binding when profile adjustment was requested;
   - no agent is bound to another agent's mutable workspace.
4. If required workspace readiness is missing or inconsistent, stop and report the missing `prepare-workspace` postconditions. Do not create, repair, or route workspace setup from this page.
5. Register generated or private skills through maintained project-skill surfaces when project-local skill registration is needed.
6. Install each participant's generated on-event, on-tick, lifecycle, and shared harness-usage skills according to its generated agent binding.
7. For mail-driven participants, bind the maintained mail support skills required by the generated agent binding. Use `houmao-agent-email-comms` for ordinary mail operations, `houmao-process-emails-via-gateway` for notifier-driven open-mail rounds, `houmao-mailbox-mgr` for mailbox administration, `houmao-agent-messaging` for managed-agent communication routing, and `houmao-agent-gateway` for gateway posture.
8. Create or update specialists and profiles through `houmao-specialist-mgr` or the supported `houmao-mgr project easy` surfaces.
9. Launch missing agents through `houmao-agent-instance` or the supported easy-instance launch surface when the execplan requests live participants.
10. Prepare mailbox, gateway, memory, and inspection posture through their owning Houmao skills.
11. Confirm mail-driven loops have the mailbox posture needed for their generated schema/render communication flow, including notifier posture when generated mail-received skills expect gateway-notified rounds.
12. Confirm mail notification prompt customization includes any loop-specific instruction to process mail through generated on-event skills and call on-tick skills after mail processing when the execplan requires it.
13. Confirm generated skills can locate the plan-local harness when they depend on dynamic objective, constraint, policy, state, schema, rendering, query, validation, or controlled-apply commands.
14. Confirm durable-execution plans have a run artifact layout ready for payloads, rendered outputs, responses, records, state files, logs, and evidence.
15. Report prepared agents, workspace readiness check, missing agents, installed generated skills, maintained mail support bindings, notifier prompt posture, harness lookup posture, run artifact posture, mailbox and gateway posture, and any launch or binding blockers.

## Constraints

- Do not hand-edit Houmao runtime internals.
- Do not call, route to, plan, execute, create, repair, or otherwise perform `prepare-workspace`.
- Do not run `houmao-utils-workspace-mgr` from this page.
- Do not create agent worktrees or workspace scaffolding by hand.
- Do not install another participant's generated event or tick skills into the wrong agent profile.
- Do not duplicate mailbox endpoint contracts, mailbox storage, gateway discovery, or ordinary mail send/read/reply/archive mechanics inside generated agent preparation.
- Do not start loop work from this page; use `start`.
- Do not invent launch profiles when the execplan or user did not provide enough information.
- Do not prepare agents to sleep, poll, tail logs, or wait in-chat for loop progress; mail notifier prompts and operator prompts are the wakeup mechanism.
