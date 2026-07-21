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

# Status

## Read First

- `../reference/direct-sqlite-state.md`
- `../reference/platform-boundaries.md`
- `../reference/system-input-questions.md`

## Inputs

Require:
- `<loop-dir>`
- run id or enough context to identify the run

## Actions

1. Read `execplan/manifest.md` and selected run artifacts.
2. Inspect SQLite state read-only according to `execplan/specs/state/README.md`.
3. Inspect generated process, pending mail refs, and artifact refs.
4. Use `<public-entrypoint>->houmao-shared-routines->agent-inspect`, mailbox, or gateway skills for live posture when needed.
5. Report run state, active participants, pending handoffs, blockers, and next operator action.

## Constraints

- Do not mutate runtime state.
- Do not send keepalive prompts.
