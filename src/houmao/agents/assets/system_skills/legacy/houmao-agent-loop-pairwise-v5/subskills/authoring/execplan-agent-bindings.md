# Execplan Agent Bindings

## Read First

- `../reference/generated-contract-defaults.md`
- MUST READ: `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`

## Preconditions

- Participant contracts, workspace contracts, generated skills, and harness surfaces are current.

## Inputs

Require:
- `<loop-dir>`;
- generated participant specs;
- generated workspace contracts when applicable;
- generated skills;
- maintained support skill requirements from the process and communication contracts.

## Outputs

Generate or update `execplan/agents/`:
- concrete agent `config.toml` files;
- concrete agent `definition.md` prompt sources;
- participant-to-agent bindings;
- installed generated skills;
- maintained support skills;
- skill installation mode;
- memo seed policy;
- workspace or launch policy;
- mail notification prompt customization when the participant is mail-driven;
- auto/manual wakeup posture when the generated loop supports manual operation.

Use this package shape for plan-local agent bindings:

```text
<loop-dir>/execplan/agents/
  README.md
  bindings.toml
  profiles/
    README.md
    <agent-id>/
      config.toml
      definition.md
      memo-seed.md
  notifier-prompts/
    README.md
    <agent-id>.md
```

`bindings.toml` maps participant instances to concrete agent ids, generated skills, maintained support skills, prompt sources, workspace policy, launch policy, and notifier prompt path when applicable. `profiles/<agent-id>/memo-seed.md` and `notifier-prompts/<agent-id>.md` are optional, but required when the binding claims memo seeding or mail notification customization. Keep live project profile creation for execution subskills.

Bindings are generated intent for concrete agents, not proof that project profiles already exist. `prepare-agents` confirms or creates the concrete profiles and reports prepared agent/profile and launch facts. `prepare-workspace` consumes those prepared facts with `workspace.toml` instead of inventing names from scratch. `launch-agents` consumes prepared launch facts after validation and reports live-agent/session facts.

Workspace requirements stay authoritative in `execplan/specs/workspace/workspace.toml`. `bindings.toml` should reference the applicable workspace policy for each concrete agent instead of restating or replacing workspace-manager inputs.

README rules:
- generated `agents/`, `agents/profiles/`, and `agents/notifier-prompts/` directories use README files with only `Purpose` and `Contents`;
- generated profile subdirectories may omit local README files when `config.toml`, `definition.md`, and optional `memo-seed.md` are self-evident and indexed by `bindings.toml`.

## Actions

1. Bind concrete Houmao agents to stable participant instances.
2. Install only the generated skills and maintained support skills needed for each participant's responsibilities.
3. Include workspace policy references, launch policy, memo policy, and concrete identity fields that `prepare-agents` can report for workspace setup and launch.
4. Keep concrete agent bindings separate from participant role templates and role instances.
5. For mail-driven participants, bind notifier prompt instructions that tell the agent to process mail through generated on-event skills and run any required on-tick skill after mail processing in default `auto` mode.
6. When manual operation is supported, ensure participant prompts or installed tick skills tell agents to query harness control context and perform one operator-prompted bounded pass in `manual` mode.
7. Ensure generated bindings install the role's mode-aware on-tick skill and any shared harness-usage skill it needs.
8. Create or update README files for emitted agent-binding directories.
9. Leave actual profile creation, live launch, mailbox setup, gateway setup, notifier enable/disable, and memory updates to execution subskills and maintained Houmao surfaces.

Example binding:

```toml
[[bindings]]
participant = "reviewer"
agent_id = "agent-a"
launch_profile = "agent-a"
workspace_policy = "workspace.agents.agent-a"
```

## Downstream Effects

- Changes here invalidate final docs and final manifest.

## Constraints

- Do not start or configure live agents from this stage.
- Do not install another participant's event or tick skills into the wrong binding.
- Do not create workspaces directly.
- Do not make agent bindings depend on in-chat waiting, sleeps, polling, or periodic tick wakeups.
- Do not describe manual mode as notifier-driven; manual mode is operator-prompted bounded work.
