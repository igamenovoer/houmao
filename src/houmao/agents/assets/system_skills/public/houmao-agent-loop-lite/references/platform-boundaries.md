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

- Agent definitions and profiles: `houmao-shared-routines->houmao-agent-definition`.
- Workspace planning, creation, validation, and summaries: `houmao-shared-routines->houmao-utils-workspace-mgr`.
- Launch, join, stop, and relaunch: `houmao-shared-routines->houmao-agent-instance`.
- Ordinary mail send, reply, read, and archive work: `houmao-shared-routines->houmao-agent-email-comms` or supported mailbox CLI surfaces.
- Gateway and notifier lifecycle: `houmao-shared-routines->houmao-agent-gateway`.
- Prompt, interrupt, and live managed-agent messages: `houmao-shared-routines->houmao-agent-messaging`.
- Liveness, logs, mailbox posture, gateway posture, and runtime inspection: `houmao-shared-routines->houmao-agent-inspect`.

## Constraints

- Do not duplicate maintained Houmao contracts inside lite specs or generated skills.
- Do not invent `houmao-mgr` surfaces.
- Use `plan`, `create`, `validate`, or `summarize` for workspace-manager operations; do not use legacy `execute` wording.
