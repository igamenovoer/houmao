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

# Launch Agents

## Read First

- `../reference/generated-contract-defaults.md`
- MUST READ: `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`
- `../reference/system-input-questions.md`

## Preconditions

- Generated execplan exists.
- Agent/project-profile facts have been prepared by `prepare-agents`.
- Workspace readiness is complete or explicitly not required.
- `validate-loop` has passed for pre-launch readiness, or the operator provides an equivalent current validation report.
- Operator wants prepared participants launched before `start`.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/execplan/manifest.toml`
- generated execplan validation evidence or a current `validate-execplan` pass
- pre-launch readiness validation report from `validate-loop`
- prepared agent/project-profile and launch facts from `prepare-agents`
- workspace readiness facts from `prepare-workspace`, including current validation evidence or summary when managed workspaces are required, or explicit manual workspace evidence

Use when present:
- generated agent bindings;
- generated run artifact contracts;
- generated notifier prompt paths;
- launch cwd and memo posture reports;
- mailbox, gateway, notifier, memory, and inspection posture reports.

## Actions

1. Confirm `validate-loop` passed for the current generated execplan revision, prepared agent/profile facts, workspace facts, and launch posture.
2. Read `execplan/manifest.toml`, generated agent bindings, prepared launch facts, workspace readiness facts or manual evidence, and run contracts.
3. Confirm every required participant has:
   - concrete agent id;
   - project profile name, or explicit raw launch profile name;
   - prompt or definition source;
   - launch cwd posture;
   - memo seed posture when required;
   - installed generated skills;
   - Houmao system-skill preinstall posture;
   - notifier prompt posture when mail-driven.
4. Confirm no required participant is already live in an incompatible session, cwd, profile, or mailbox posture.
5. Launch missing live agents through `<public-entrypoint>->houmao-shared-routines->agent-instance` or supported `houmao-mgr project` launch surfaces.
6. Inspect launched or already-live agents through maintained inspection surfaces when needed to confirm liveness and session identity.
7. Do not send loop-start prompts, mail, or work payloads.

## Report

Report:
- launched agents and already-live agents;
- concrete agent ids, project profile or explicit raw launch profile names, session ids, cwd, and mailbox posture when known;
- launch surface used;
- participants not launched and why;
- warnings that `start` should check;
- whether `start` may proceed with only final lightweight liveness and start-trigger checks.

## Constraints

- Do not create or repair profiles, specialists, generated skills, system-skill posture, workspaces, mailboxes, gateways, memories, harness state, run artifacts, or generated execplan files.
- Do not call or route to `prepare-agents`, `prepare-workspace`, or `validate-loop` as normal behavior.
- Do not launch agents when required pre-launch readiness evidence is missing or stale.
- Do not deliver first loop work, start triggers, generated mail, or participant task prompts.
- Do not ask agents to wait in-chat for future mail or tick work.
