# Prepare Agents

## Read First

- `../reference/generated-contract-defaults.md`
- MUST READ: `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`
- `../reference/system-input-questions.md`

## Preconditions

- Generated execplan exists.
- Operator wants concrete agents, profiles, launch facts, skill bindings, support-skill requirements, notifier prompts, and memo posture prepared before workspace setup.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/execplan/manifest.toml`
- generated agent bindings under `<loop-dir>/execplan/agents/`
- generated skills under `<loop-dir>/execplan/skills/`
- generated workspace contracts when the execplan requires managed workspaces

## Actions

1. Validate the execplan before preparing agents.
2. Read `execplan/manifest.toml`, generated participant specs, generated workspace contracts, generated agent bindings, generated run artifact contracts, and generated harness docs or commands to identify required concrete agents, launch profiles, participant roles, workdirs, skill bindings, memo or prompt sources, dynamic lookup surfaces, and run artifact paths.
3. Register generated or private skills through maintained project-skill surfaces when project-local skill registration is needed.
4. Install each participant's generated on-event, on-tick, lifecycle, and shared harness-usage skills according to its generated agent binding.
5. For mail-driven participants, bind the maintained mail support skills required by the generated agent binding. Use `houmao-agent-email-comms` for ordinary mail operations, `houmao-process-emails-via-gateway` for notifier-driven open-mail rounds, `houmao-mailbox-mgr` for mailbox administration, `houmao-agent-messaging` for managed-agent communication routing, and `houmao-agent-gateway` for gateway posture.
6. Create or update specialists and profiles through `houmao-agent-definition` or the supported `houmao-mgr project` surfaces.
7. Prepare prompt sources, notifier prompt material, memo seed posture, and profile mutation intent that may later receive workspace cwd or workspace memo rules.
8. Resolve and record concrete facts needed by `prepare-workspace`:
   - concrete agent ids;
   - launch profile names;
   - stable workspace agent names;
   - prompt or definition sources;
   - installed generated skills;
   - maintained support skills;
   - notifier prompt paths;
   - memo seed paths or pending memo posture;
   - launch cwd policy or pending launch cwd posture;
   - whether a matching live agent was observed without launching it.
9. Prepare mailbox, gateway, memory, and inspection posture through their owning Houmao skills when those preparations do not depend on pending workspace setup.
10. Confirm mail notification prompt customization includes any loop-specific instruction to process mail through generated on-event skills and call on-tick skills after mail processing when the execplan requires it.
11. Report prepared agent/profile facts, prepared launch facts, observed already-live agents, installed generated skills, maintained mail support bindings, notifier prompt posture, memo posture, harness lookup dependencies, mailbox and gateway posture, and blockers for `prepare-workspace`, `validate-loop`, or `launch-agents`.

## Constraints

- Do not hand-edit Houmao runtime internals.
- Do not call, route to, plan, execute, create, repair, or otherwise perform `prepare-workspace`.
- Do not run `houmao-utils-workspace-mgr` from this page.
- Do not create agent worktrees or workspace scaffolding by hand.
- Do not require workspace readiness before preparing concrete agent/profile facts.
- Do not launch live agents as normal preparation behavior; use `launch-agents`.
- Do not install another participant's generated event or tick skills into the wrong agent profile.
- Do not duplicate mailbox endpoint contracts, mailbox storage, gateway discovery, or ordinary mail send/read/reply/archive mechanics inside generated agent preparation.
- Do not start loop work from this page; use `start`.
- Do not invent launch profiles when the execplan or user did not provide enough information.
- Do not prepare agents to sleep, poll, tail logs, or wait in-chat for loop progress; mail notifier prompts and operator prompts are the wakeup mechanism.
