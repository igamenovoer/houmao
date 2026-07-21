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

# Routing Boundaries

Use this reference when a project-related task is close to another renamed Houmao skill and the ownership line needs to stay explicit.

## `<public-entrypoint>->houmao-shared-routines->project-mgr` Owns

- project overlay lifecycle: `project init`, `project status`
- project layout and overlay-resolution explanation
- project-scoped easy-instance inspection or stop: `project agents list|get|stop`

## Route To Other Skills

- `<public-entrypoint>->houmao-shared-routines->agent-definition` for `roles`, `recipes`, `launch-dossiers`, `specialists`, `profiles`, `create-agent-fast-forward`, `launch-agent`, and `stop-agent`
- `<public-entrypoint>->houmao-shared-routines->credential-mgr` for `project [--project-dir <dir>] credentials <tool> list|get|add|set|rename|remove` and `internals native-agent credentials <tool> ... --native-agent-root <path>`
- `<public-entrypoint>->houmao-shared-routines->agent-instance` for general live-agent lifecycle after project-scoped routing
- `<public-entrypoint>->houmao-shared-routines->mailbox-mgr` for `mailbox ...`, `project mailbox ...`, and `agents single ... mailbox ...` or `agents self mailbox ...`

## Notes

- Raw-profile `--auth` changes are profile authoring, not auth-bundle CRUD.
- Project context explanations may mention other command families, but that does not transfer ownership of those workflows away from their dedicated skills.
- Do not use obsolete `houmao-manage-*` identifiers as current routing targets.
