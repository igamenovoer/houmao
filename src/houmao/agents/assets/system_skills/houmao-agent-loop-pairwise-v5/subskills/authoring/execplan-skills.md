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

Use this package shape for generated skills:

```text
<loop-dir>/execplan/skills/
  <unique-skill-name>/
    SKILL.md
    agents/
      openai.yaml
```

All generated skills live directly under `execplan/skills/`. Do not create nested category directories such as `shared/`, `on-event/`, `on-tick/`, or `operator/`. Do not place generated skill Markdown as loose files directly under `execplan/skills/`; every generated skill must be a skill directory with `SKILL.md`.

Skill names must be unique after installation. Use stable generated names that encode the loop package or participant role plus the trigger or purpose, such as `<loop-slug>-<role>-<event>` or `<loop-slug>-<role>-tick`, when shorter names could collide.

## Actions

1. Generate shared harness-usage guidance before role-specific generated skills.
2. Generate on-event skills for concrete events or message families that need role-owned behavior.
3. For mail-driven loops, state that mail-received on-event skills are normally entered from Houmao notifier prompts after the separate mail notifier detects open mail.
4. Generate on-tick skills for scheduling, reconciliation, timeout, completion, or "what now" behavior that does not belong to one incoming event.
5. When a tick should follow mail processing, put that rule in notifier prompt guidance or equivalent agent binding material.
6. Generate operator skills only for loop-local runbook behavior and routing to maintained Houmao operation skills.
7. Keep each generated skill bounded to one trigger, role, or lifecycle responsibility.
8. Reference generated schemas, harness commands, maintained support skills, and stopping points explicitly.
9. Make generated skills finish after their bounded work; they must not wait in-chat for future mail or future ticks.

## Downstream Effects

- Changes here invalidate concrete agent bindings, final docs, and final manifest.

## Constraints

- Do not install generated skills into agents in this stage.
- Do not duplicate maintained Houmao platform-operation contracts.
- Do not bake dynamic policy values into static generated skill prose when a spec, state, or harness lookup should own them.
- Do not implement sleep, polling, log tailing, or in-chat waiting as loop control.
- Do not describe on-tick skills as periodic background workers; they are invoked from notifier or operator prompt turns and perform one bounded pass.
