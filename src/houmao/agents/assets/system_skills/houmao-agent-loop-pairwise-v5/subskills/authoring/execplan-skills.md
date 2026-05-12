# Execplan Skills

## Read First

- `../reference/generated-contract-defaults.md`
- MUST READ: `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`

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
- shared harness-usage skill;
- role on-event skills;
- role on-tick skills;
- operator lifecycle or workspace-router skills;
- optional `agents/openai.yaml`.

## Package Shape

```text
<loop-dir>/execplan/skills/
  README.md
  <unique-skill-name>/
    SKILL.md
    agents/
      openai.yaml
```

Rules:
- `execplan/skills/README.md` describes the generated skill collection with only `Purpose` and `Contents`.
- All generated skills live directly under `execplan/skills/`.
- Do not create category directories such as `shared/`, `on-event/`, `on-tick`, or `operator/`.
- Do not place loose Markdown files directly under `execplan/skills/`.
- Skill names must be unique after installation.
- Encode loop, role, trigger, or purpose in the skill name.
- A generated skill directory that contains only `SKILL.md` and optional `agents/openai.yaml` does not need its own `README.md`.
- If a generated skill directory contains additional generated files, add a local `README.md` using only `Purpose` and `Contents`.

Name examples:

```text
<loop-slug>-shared-harness
<loop-slug>-<role>-on-<message-family>
<loop-slug>-<role>-tick
<loop-slug>-operator-runbook
```

## Creation Method

Prefer the active tool's native skill creator when available:
- use it to create the skill directory and base `SKILL.md`;
- replace generated placeholder prose with loop-specific content;
- keep generated names and descriptions stable.

Examples:

```bash
# Codex-style helper, when available in the active environment
python <skill-creator>/scripts/init_skill.py <unique-skill-name> --path <loop-dir>/execplan/skills

# Houmao project registration happens later, during prepare-agents
houmao-mgr project skills add --name <unique-skill-name> --source <loop-dir>/execplan/skills/<unique-skill-name>
```

If no native creator is available, create the directory manually with the same required shape.

## Skill File Contract

Every generated `SKILL.md` must have YAML frontmatter:

```markdown
---
name: <unique-skill-name>
description: Use when <role-or-operator> must handle <trigger-or-purpose> for the generated <loop-slug> loop.
---

# <Skill Title>

## Trigger

- <event, tick, lifecycle command, or shared usage case>

## Inputs

- <mail family, harness command, state query, contract path, or operator command>

## Procedure

1. <bounded step>
2. <bounded step>
3. <send reply, apply record, query state, or report result>

## Output

- <reply, record, state update, handoff, or no-action report>

## Stop

- End the turn after this bounded work.
```

Style:
- concise sections;
- one trigger or purpose per skill;
- concrete file paths, schema ids, and harness command names;
- no duplicated platform-operation instructions already owned by maintained Houmao skills.

## Actions

1. Generate shared harness-usage guidance before role-specific generated skills.
2. Generate on-event skills for concrete events or message families.
3. Generate on-tick skills for scheduling, reconciliation, timeout, completion, or "what now" work.
4. Generate operator skills only for loop-local runbooks and routing to maintained Houmao skills.
5. For mail-driven loops, state that mail-received skills are entered from Houmao notifier prompts after the separate notifier detects open mail.
6. When a tick should follow mail processing, put that rule in notifier prompt guidance or equivalent agent binding material.
7. Create or update `execplan/skills/README.md`.
8. Add generated skill-directory README files only when that skill directory contains extra generated files beyond `SKILL.md` and optional `agents/openai.yaml`.
9. Reference generated schemas, harness commands, maintained support skills, and stopping points explicitly.

## Downstream Effects

- Changes here invalidate concrete agent bindings, final docs, and final manifest.

## Constraints

- Do not install generated skills into agents in this stage.
- Do not duplicate maintained Houmao platform-operation contracts.
- Do not bake dynamic policy values into static generated skill prose when a spec, state, or harness lookup should own them.
- Do not implement sleep, polling, log tailing, or in-chat waiting as loop control.
- Do not describe on-tick skills as periodic background workers; they are invoked from notifier or operator prompt turns and perform one bounded pass.
- Do not let generated skill bodies grow into long essays; prefer short procedures plus references to generated contracts and harness commands.
