---
skill_invocation_notation: >
  Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
  SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
  accepted only as legacy input when SKILL-MAIN.md is absent.
  Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
  `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
  `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
  subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
  by parent subcommand parent. Intermediate subcommands act as object generators.
  Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints.
---

# Execplan Skills

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

## Read First

- `../reference/generated-contract-defaults.md`
- `../reference/topology-modes.md`
- `../reference/predecessor-context.md`
- `../reference/mail-schema-events.md`
- `../reference/result-routing.md`
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
- `<loop-slug>-operator-control` for lifecycle, mode, manual-step, and recovery control when the loop has those needs;
- other operator lifecycle or workspace-router skills only when justified by the process;
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
<loop-slug>-operator-control
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
2. Generate on-event skills for concrete events or message families; mail-received on-event skills name the triggering `schema_id`.
3. Generate on-tick skills for scheduling, reconciliation, timeout, completion, or "what now" work.
4. Generate `<loop-slug>-operator-control` when the loop has lifecycle, mode, recovery, or manual-step needs.
5. Generate other operator skills only for loop-local runbooks and routing to maintained Houmao skills.
6. For mail-driven loops, state that mail-received skills are entered from Houmao notifier prompts after the separate notifier detects open mail.
7. Generated skills read topology mode from specs, state, or harness output before choosing reply, forward, cycle, or terminal behavior.
8. In `tree-loop`, participant skills return normal results to immediate upstream unless a generated terminal or operator exception exists.
9. In `generic-loop`, participant skills preserve selected carried context when forwarding or replying if the generated contracts require it; if a route records explicit no-context-needed omission, do not invent context.
10. When a tick should follow mail processing, put that rule in notifier prompt guidance or equivalent agent binding material.
11. Create or update `execplan/skills/README.md`.
12. Add generated skill-directory README files only when that skill directory contains extra generated files beyond `SKILL.md` and optional `agents/openai.yaml`.
13. Reference generated schemas, `schema_id` triggers, topology/context harness commands, Houmao system-skill availability, and stopping points explicitly.

## On-Event Mail Skills

For each generated mail event skill:
- name the exact triggering `schema_id` in `Trigger`;
- identify the role owner and expected participant id or role;
- inspect the in-body `houmao-email-metadata` block before acting;
- treat sender-side schema validation as ordinary-case input posture;
- semantically inspect the readable body and selected context;
- use harness commands for state, topology, context, rendering, or lifecycle updates when generated;
- send the generated reply or forward family when required;
- archive or close the source mail only after successful processing when the mail policy requires it;
- stop after one bounded event.

Unknown, malformed, operator-origin, or freeform mail uses generated fallback skills only when the process defines them.

## Operator Control Skill

When generated, `<loop-slug>-operator-control` must:

- identify the loop slug, loop dir, manifest path, harness path, agent binding path, and supported lifecycle operations;
- cover status, start, pause, resume, stop, recover, mode switching, and manual step only when those operations apply;
- route notifier posture to `houmao-shared-routines->houmao-agent-gateway`;
- route operator prompts to `houmao-shared-routines->houmao-agent-messaging`;
- route ordinary mail work to `houmao-shared-routines->houmao-agent-email-comms`;
- query or update generated harness control commands for run state, execution mode, and operator intent records.

It may include local subskill or reference pages such as:

```text
<loop-slug>-operator-control/
  SKILL.md
  README.md
  subskills/
    status.md
    start.md
    set-mode.md
    pause.md
    resume.md
    stop.md
    recover.md
    manual-step.md
```

## On-Tick Mode Behavior

For controllable loops, generated on-tick skills must:

- query harness control context before deciding work;
- branch between `auto` and `manual` when both modes apply;
- in `auto`, perform the notifier-prompted bounded follow-up tick;
- in `manual`, inspect current mail or state as needed, do one bounded action, apply records through the harness, send or reply when required, and stop;
- report no action when nothing is actionable;
- end the chat turn after one pass.

## Downstream Effects

- Changes here invalidate concrete agent bindings, final docs, and final manifest.

## Constraints

- Do not install generated skills into agents in this stage.
- Do not duplicate maintained Houmao platform-operation contracts.
- Do not bake dynamic policy values into static generated skill prose when a spec, state, or harness lookup should own them.
- Do not implement sleep, polling, log tailing, or in-chat waiting as loop control.
- Do not describe on-tick skills as periodic background workers; they are invoked from notifier or operator prompt turns and perform one bounded pass.
- Do not make manual-mode tick behavior wait in-chat for future mail or status changes.
- Do not let generated skill bodies grow into long essays; prefer short procedures plus references to generated contracts and harness commands.
