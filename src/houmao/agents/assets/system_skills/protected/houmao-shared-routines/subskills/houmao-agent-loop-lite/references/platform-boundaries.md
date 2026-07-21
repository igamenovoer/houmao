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

# Platform Boundaries

## Maintained Surfaces

- Agent definitions and profiles: `<public-entrypoint>->houmao-shared-routines->agent-definition`.
- Workspace planning, creation, validation, and summaries: `<public-entrypoint>->houmao-shared-routines->utils-workspace-mgr`.
- Launch, join, stop, and relaunch: `<public-entrypoint>->houmao-shared-routines->agent-instance`.
- Ordinary mail send, reply, read, and archive work: `<public-entrypoint>->houmao-shared-routines->agent-email-comms` or supported mailbox CLI surfaces.
- Gateway and notifier lifecycle: `<public-entrypoint>->houmao-shared-routines->agent-gateway`.
- Prompt, interrupt, and live managed-agent messages: `<public-entrypoint>->houmao-shared-routines->agent-messaging`.
- Liveness, logs, mailbox posture, gateway posture, and runtime inspection: `<public-entrypoint>->houmao-shared-routines->agent-inspect`.

## Constraints

- Do not duplicate maintained Houmao contracts inside lite specs or generated skills.
- Do not invent `houmao-mgr` surfaces.
- Use `plan`, `create`, `validate`, or `summarize` for workspace-manager operations; do not use legacy `execute` wording.
