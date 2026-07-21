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

# Execplan Specs Contract

## Read First

- `../reference/markdown-contract-defaults.md`
- `../reference/markdown-template-events.md`
- `../reference/direct-sqlite-state.md`
- `../reference/platform-boundaries.md`

## Inputs

Require:
- `<loop-dir>`
- `execplan/specs/process.md`

## Outputs

Generate or update Markdown contracts:
- `execplan/specs/objective.md`
- `execplan/specs/organization.md`
- `execplan/specs/communication.md`
- `execplan/specs/templates/*.md`
- `execplan/specs/state/README.md`
- `execplan/specs/state/schema.sql` when durable state is needed
- optional `workspace.md` and `run-artifacts.md`

## Actions

1. Derive contracts from process and intention source.
2. Define typed Markdown templates with `Loop-Template-Type` and `Loop-Template-Version`.
3. Define direct SQLite state tables when stable bookkeeping is needed.
4. Route workspace requirements to `<public-entrypoint>->houmao-shared-routines->utils-workspace-mgr` when standard workspace setup applies.
5. Keep optional concerns absent when the loop does not need them.

## Constraints

- Do not create TOML registries, JSON schemas, Jinja2 renderers, or harness commands.
