---
metadata:
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

Generated lite Markdown contracts and skills own loop-local workflow semantics; maintained Houmao routines own all platform mechanics.

## Maintained Surfaces

- Agent definitions, specialists, project profiles, and `project skills`: `houmao-shared-routines->houmao-agent-definition`.
- Workspace `plan`, `create`, `validate`, and `summarize`: `houmao-shared-routines->houmao-utils-workspace-mgr`.
- Live instance `launch`, `join`, `relaunch`, `stop`, `cleanup`, and `agents external`: `houmao-shared-routines->houmao-agent-instance`.
- Gateway admission policy, `default-group`, roles/templates, grants, and peer/`self-key` management: `houmao-shared-routines->houmao-agent-access`.
- Authorized `workspace`, `memory`, `skills`, and `mcp` mount reads, patches, and `publish`: `houmao-shared-routines->houmao-agent-files`.
- Offline mailbox setup/repair/cleanup/export and `mailbox online` Stalwart JMAP bindings: `houmao-shared-routines->houmao-mailbox-mgr`.
- Ordinary mail `status`/`list`/`read`/`peek`/`send`/`post`/`reply`/`mark`/`move`/`archive` and bounded notifier rounds: `houmao-shared-routines->houmao-agent-email-comms` and `houmao-shared-routines->houmao-process-emails-via-gateway`.
- Gateway lifecycle, notifier/reminder services, web-entry, and optional plugins (`houmao-cccc`): `houmao-shared-routines->houmao-agent-gateway`.
- Live peer/self `request`, `prompt`, `interrupt`, and mailbox handoff: `houmao-shared-routines->houmao-agent-messaging`.
- Birth-time memo seeds and live `pages/` memory updates: `houmao-shared-routines->houmao-memory-mgr`.
- Read-only liveness, `state`, logs, usage records, artifacts, and socket-qualified `tmux -S` inspection: `houmao-shared-routines->houmao-agent-inspect`.

## Constraints

- Do not duplicate maintained Houmao CLI or gateway contracts inside lite Markdown specs or generated skills.
- Do not invent `houmao-mgr` subcommands or use retired `execute` wording for workspace-manager actions (`plan`, `create`, `validate`, `summarize`).
