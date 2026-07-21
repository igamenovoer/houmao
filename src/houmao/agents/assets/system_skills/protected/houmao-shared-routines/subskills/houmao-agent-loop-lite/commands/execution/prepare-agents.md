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

# Prepare Agents

## Read First

- `../reference/markdown-contract-defaults.md`
- `../reference/platform-boundaries.md`
- `../reference/system-input-questions.md`

## Inputs

Require:
- `<loop-dir>`
- `execplan/manifest.md`
- `execplan/agents/bindings.md`
- generated skills under `execplan/skills/`

## Actions

1. Read manifest, agent bindings, generated skill index, and profile material when present.
2. Resolve each participant's concrete agent or profile name, selected tool, credential, generated skill groups, memo posture, launch interface mode (`tui` or `headless`), and workdir or pending workspace policy.
3. Route participant definition and profile preparation through `<public-entrypoint>->houmao-shared-routines->agent-definition`.
4. Record prepared agent/profile facts for `prepare-workspace`, `validate-loop`, and `launch-agents`.
5. Treat unknown, missing, or contradictory TUI/headless launch mode facts as preparation blockers unless the operator accepts a documented manual raw launch profile.
6. Do not launch live agents.

## Report

Report readiness, prepared profile facts, installed generated skills, system-skill preinstall posture, memo posture, pending workspace-dependent mutations, blockers, and warnings.

End with one Markdown table:

| Agent | Participant | Launch mode | Credential | Skill groups | Workdir |
| --- | --- | --- | --- | --- | --- |
| `<agent-id or profile>` | `<participant or role>` | `tui` or `headless` | `<credential display name or unknown>` | `<generated/private skill group names>` | `<launch cwd or pending workspace policy>` |

Use `blocked` in a cell when a required fact is missing or inconsistent, then list the blocker above the table.

## Constraints

- Do not reimplement specialist creation, project-profile mutation, launch-dossier mutation, credential defaulting, or launcher selection.
- Do not prepare workspaces, mailboxes, gateways, memories, run artifacts, or live sessions here.
