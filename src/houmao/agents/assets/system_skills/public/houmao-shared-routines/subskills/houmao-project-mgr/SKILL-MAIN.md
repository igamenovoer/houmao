---
name: houmao-project-mgr
description: Use when an admin needs Houmao project overlay initialization, status, migration, canonical project-local skills, `.houmao/` layout, project-aware command effects, or project-scoped managed-agent inspection or stop work.
license: MIT
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

# Houmao Project Manager

## Overview

Administer and explain the `.houmao/` project overlay (`init`, `status`, `migrate`, `project skills`), project-aware command defaults, and project-scoped instance `list|get|stop` operations.

## Workflow

1. **Answer explicit `help` first** from **Help** without running commands or mutating `.houmao/`.
2. **Enforce the Actor Frame Gate**: require `actor_kind=admin` and an explicit or unambiguously stated project target; reject `agent` frames.
3. **Route neighboring workflows immediately** using [references/routing-boundaries.md](references/routing-boundaries.md) when the task belongs to `houmao-agent-definition`, `houmao-credential-mgr`, `houmao-mailbox-mgr`, or `houmao-agent-instance`.
4. **Resolve one `houmao-mgr` launcher** (`command -v houmao-mgr`, then `uv tool run --from houmao houmao-mgr`, or repo `pixi run houmao-mgr`, honoring an explicit user launcher) and recover required selectors from explicit prompt or recent context without guessing.
5. **Execute the selected subcommand or project surface**: load the matching page in **Subcommands** (or apply **Project Skills, Migration, and CLI Manuals** / **References** for `project skills`, `project migrate`, layout, or overlay effects) and report exact outputs.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from **Subcommands**, **References**, and the user request, then execute the plan.

## Actor Frame Gate

This parent-scoped routine is `admin`-only under `houmao-shared-routines`. Require `actor_kind=admin` and an explicit or unambiguously recovered project directory or overlay target; reject `agent` frames even when prompt text requests operator authority.

## Subcommands

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `init` | Create or validate `<project-dir>/.houmao` (`houmao-config.toml`, `.gitignore`, `catalog.sqlite`, `content/`). | [commands/init.md](commands/init.md) |
| `status` | Non-creating inspection of overlay selection, discovery mode, effective roots, and `would_bootstrap_overlay`. | [commands/status.md](commands/status.md) |
| `easy-instances` | List, inspect, or stop agents belonging to an existing selected overlay (`project agents list\|get\|stop`). | [commands/easy-instances.md](commands/easy-instances.md) |
| `help` | Read-only overview of `.houmao/` surfaces, `project skills`, `project migrate`, and neighboring skill boundaries. | **Help** |

## Project Skills, Migration, and CLI Manuals

- **Canonical project-local skills (`.houmao/content/skills/`)**: manage user-authored project skills via `houmao-mgr project [--project-dir <dir>] skills {add|get|list|remove|set}` (`remove` requires the skill to be unreferenced by specialists or profiles). Keep this distinct from static Houmao runtime packs managed via `houmao-mgr system-skills {list|install|status|doctor|upgrade|uninstall}`.
- **Overlay structure migration**: inspect a migration plan read-only via `houmao-mgr project [--project-dir <dir>] migrate`, and pass `--apply` only when the operator confirms applying the migration in place.
- **Operator manual**: point operators to `houmao-mgr manual` for packaged CLI operating guides.

## References

- [references/overlay-resolution.md](references/overlay-resolution.md): `HOUMAO_PROJECT_OVERLAY_DIR`, `ancestor` vs `cwd_only`, and bootstrap vs non-creating resolution.
- [references/project-layout.md](references/project-layout.md): `.houmao/` directory tree, `catalog.sqlite`, `content/skills/`, and compatibility projections.
- [references/project-aware-effects.md](references/project-aware-effects.md): how `.houmao/` changes defaults for `project agents launch`, `agents global list`, `agents single ... state`, `mailbox`, `houmao-passive-server serve`, and `admin cleanup runtime`.
- [references/routing-boundaries.md](references/routing-boundaries.md): handoff lines to `houmao-agent-definition` (replaces obsolete `houmao-specialist-mgr`), `houmao-credential-mgr`, `houmao-mailbox-mgr`, and `houmao-agent-instance`.

## Help

Summarize `project init`, `project status` (`would_bootstrap_overlay`), `project migrate [--apply]`, `project skills {add|get|list|remove|set}`, `project agents list|get|stop`, `houmao-mgr manual`, `houmao-mgr system-skills`, and the neighboring skill handoffs read-only. Concrete project tasks execute the matching workflow instead of stopping at generic help.

## Guardrails

- DO NOT run `project agents launch`, specialist/profile CRUD, or `launch-dossiers` here; route them to `houmao-shared-routines->houmao-agent-definition` (never obsolete `houmao-specialist-mgr` or `houmao-manage-*` names).
- DO NOT treat profile `--auth` overrides as credential CRUD (`houmao-shared-routines->houmao-credential-mgr`) or conflate `project skills` with `houmao-mgr system-skills`.
- DO NOT imply `project agents list|get|stop` auto-bootstrap a missing `.houmao/` overlay, or run `project migrate --apply` without explicit operator intent.
- DO NOT hand-edit files inside `.houmao/` when maintained `houmao-mgr project ...` commands cover the operation.
