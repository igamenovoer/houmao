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

# Routing Boundaries

Use this reference to keep ownership explicit between `houmao-project-mgr`, neighboring shared routines, and direct operator CLI utilities.

## `houmao-shared-routines->houmao-project-mgr` Owns

- Project overlay lifecycle and migration: `houmao-mgr project init`, `project status`, and `project migrate [--apply]`.
- Canonical project-local skill registry: `houmao-mgr project skills {add|get|list|remove|set}` under `.houmao/content/skills/`.
- `.houmao/` layout, overlay discovery (`HOUMAO_PROJECT_OVERLAY_DIR`, `ancestor`, `cwd_only`), and project-aware default explanations.
- Project-scoped instance inspection and stop: `houmao-mgr project agents list|get|stop`.

## Route to Neighboring Routines or Direct Operator CLIs

- **`houmao-shared-routines->houmao-agent-definition`** (canonical replacement for obsolete `houmao-specialist-mgr`): `roles`, `recipes`, `launch-dossiers`, `specialists`, `profiles`, `recipe-profiles`, `definition-authoring`, `definition-deployment`, `definition-batch`, `create-agent-fast-forward`, `launch-agent` (`project agents launch`), and `stop-agent`.
- **`houmao-shared-routines->houmao-credential-mgr`**: `project [--project-dir <dir>] credentials <tool> {list|get|add|set|login|rename|remove}` and `internals native-agent credentials <tool> ... --native-agent-root <path>` (`claude`, `codex`, `dsh`, `kimi`; `login` for `claude|codex`). Profile `--auth` overrides stay in `houmao-agent-definition`.
- **`houmao-shared-routines->houmao-mailbox-mgr`**: `mailbox ...`, `project mailbox ...`, and `agents single|self ... mailbox {offline|online} ...`.
- **`houmao-shared-routines->houmao-agent-instance`**: general live-agent lifecycle (`relaunch`, `cleanup`, `agents external`, `admin executors`, `native-resources`, `runtime-variables`, `mindsets`, `private-workspace`).
- **Direct operator CLIs**: `houmao-mgr manual` for packaged operating manuals and `houmao-mgr system-skills {list|install|status|doctor|upgrade|uninstall}` for static `admin`/`agent` system-skill packs.

Never route to obsolete `houmao-manage-*` or standalone `houmao-specialist-mgr` identifiers.
