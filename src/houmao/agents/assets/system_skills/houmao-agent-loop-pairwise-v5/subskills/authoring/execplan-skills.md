# Execplan Skills

## Preconditions

- Process specs, derived contracts, and harness surfaces are current.

## Inputs

Require:
- `<loop-dir>`;
- generated process specs;
- generated communication, state, record, workspace, and participant contracts as applicable;
- generated harness docs or command descriptions when skills depend on harness behavior.

## Outputs

Generate or update `execplan/skills/`:
- shared harness-usage skills;
- role on-event skills;
- on-tick skills;
- operator lifecycle or workspace-router skills;
- skill metadata such as `agents/openai.yaml` when needed.

## Actions

1. Generate shared harness-usage guidance before role-specific generated skills.
2. Generate on-event skills for concrete events or message families that need role-owned behavior.
3. Generate on-tick skills for scheduling, reconciliation, timeout, completion, or "what now" behavior that does not belong to one incoming event.
4. Generate operator skills only for loop-local runbook behavior and routing to maintained Houmao operation skills.
5. Keep each generated skill bounded to one trigger, role, or lifecycle responsibility.
6. Reference generated schemas, harness commands, maintained support skills, and stopping points explicitly.

## Downstream Effects

- Changes here invalidate concrete agent bindings, final docs, and final manifest.

## Constraints

- Do not install generated skills into agents in this stage.
- Do not duplicate maintained Houmao platform-operation contracts.
- Do not bake dynamic policy values into static generated skill prose when a spec, state, or harness lookup should own them.
