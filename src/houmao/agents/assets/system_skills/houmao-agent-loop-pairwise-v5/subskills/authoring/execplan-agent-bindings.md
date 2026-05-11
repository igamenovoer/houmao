# Execplan Agent Bindings

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
- workspace or launch policy.

## Actions

1. Bind concrete Houmao agents to stable participant instances.
2. Install only the generated skills and maintained support skills needed for each participant's responsibilities.
3. Include workspace and memo policy when the generated loop needs those facts.
4. Keep concrete agent bindings separate from participant role templates and role instances.
5. Leave actual profile creation, launch, mailbox setup, gateway setup, and memory updates to execution subskills and maintained Houmao surfaces.

## Downstream Effects

- Changes here invalidate final docs and final manifest.

## Constraints

- Do not start or configure live agents from this stage.
- Do not install another participant's event or tick skills into the wrong binding.
- Do not create workspaces directly.
