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

# Launch Dossiers Have Moved

This file is retained only as a routing note for older installed copies.

Use `<public-entrypoint>->houmao-shared-routines->agent-definition` subcommand `launch-dossiers` for explicit recipe-backed launch-profile authoring through `internals native-agent launch-dossiers list|get|add|set|remove`.

Current local route: `houmao-agent-definition/commands/low-level/launch-dossiers.md`.

Do not run launch-profile authoring from `<public-entrypoint>->houmao-shared-routines->project-mgr`.
