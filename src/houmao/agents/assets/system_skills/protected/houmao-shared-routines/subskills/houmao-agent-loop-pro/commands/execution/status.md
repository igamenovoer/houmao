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

- `../reference/generated-contract-defaults.md`
- `../reference/platform-boundaries.md`
- `../reference/system-input-questions.md`

## Preconditions

- User wants read-only inspection of one loop.

## Inputs

Require:
- `<loop-dir>`
- the run identity or enough context to identify the generated loop run

## Actions

1. Read `execplan/manifest.toml` to locate generated status, harness, run artifact, or docs surfaces.
2. Query generated operator-control guidance or harness `control status` when available.
3. Query generated harness status, validation, completion, or view commands when available.
4. Inspect the generated run artifact layout for recorded payloads, responses, records, state, logs, evidence, and blockers when those artifacts exist.
5. Use `<public-entrypoint>->houmao-shared-routines->agent-inspect` for managed-agent liveness, screen, logs, mailbox posture, gateway state, or artifacts.
6. Use mailbox or gateway skills only for read-oriented status when needed.
7. Report current run state, execution mode, notifier posture, active participants, pending handoffs, blockers, relevant run artifacts, and the next expected operator action.

## Constraints

- Do not mutate runtime state.
- Do not send keepalive prompts as part of status.
- Do not infer completion from stale intention notes.
- Do not inspect raw runtime internals when a maintained status surface exists.
