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

# Prepare Workspace

## Read First

- `../reference/markdown-contract-defaults.md`
- `../reference/platform-boundaries.md`
- `../reference/system-input-questions.md`

## Inputs

Require:
- `<loop-dir>`
- `execplan/manifest.md`
- prepared agent/profile facts when workspace setup is required

Use when present:
- `execplan/specs/workspace.md`
- `execplan/agents/bindings.md`

## Actions

1. If no workspace contract is present and manifest records no workspace need, report no workspace setup required.
2. When standard Houmao workspace setup is required, route planning, creation, validation, or summaries through `<public-entrypoint>->houmao-shared-routines->utils-workspace-mgr`.
3. Use prepared agent names and profile facts from `prepare-agents`.
4. Verify manual workspace evidence only when the execplan permits custom operator-owned setup.
5. Report planned, created, validated, summarized, missing, inconsistent, and custom/manual facts.

## Constraints

- Do not install skills, create specialists, launch agents, bind mailboxes, or call `prepare-agents`.
- Do not use legacy workspace-manager `execute` wording.
