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

# Prepare Agents

Prepare Houmao project profiles, skill bindings, and participant launch facts from `<loop-dir>/execplan/` without launching live sessions.

## Read First

- [../../references/markdown-contract-defaults.md](../../references/markdown-contract-defaults.md)
- [../../references/platform-boundaries.md](../../references/platform-boundaries.md)
- [../../references/system-input-questions.md](../../references/system-input-questions.md)

## Workflow

1. Require `<loop-dir>`, `execplan/manifest.md`, `execplan/agents/bindings.md`, and generated skills under `execplan/skills/`.
2. Resolve each participant's concrete agent or profile name, tool (`claude`, `codex`, `kimi`, `dsh`), qualified launch mode (`Claude: headless|tui`, `Codex: headless|service|tui`, `Kimi: headless|service|tui|web`, `DSH: headless|service|web`), credential, generated/project skill groups, memo posture, and launch cwd or pending workspace policy.
3. Route specialist, project-profile, and `project skills` preparation through `houmao-shared-routines->houmao-agent-definition`.
4. Flag unknown, missing, or tool-incompatible launch modes (`headless`, `service`, `tui`, `web`) as preparation blockers unless the operator explicitly provides a documented manual raw launch profile.
5. Record prepared participant facts for `prepare-workspace`, `validate-loop`, and `launch-agents`, then emit the report below without starting live agents.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this procedure, its owning skill constraints, available references, and the user request, then execute the plan.

## Report

Report readiness, prepared profile facts, installed generated skills, `system_skills` preinstall posture, memo posture, pending workspace-dependent mutations, blockers, and warnings, ending with one summary table:

| Agent | Participant | Launch mode | Credential | Skill groups | Workdir |
| --- | --- | --- | --- | --- | --- |
| `<agent-id or profile>` | `<participant or role>` | `headless`, `service`, `tui`, or `web` | `<credential or unknown>` | `<generated/project skill groups>` | `<launch cwd or pending workspace policy>` |

Mark missing or inconsistent cells `blocked` and explain each blocker above the table.

## Guardrails

- DO NOT reimplement specialist creation, project-profile mutation, launch-dossier editing, credential defaulting, or launcher selection owned by `houmao-shared-routines->houmao-agent-definition`.
- DO NOT prepare workspaces, mailboxes, gateways, live memories, `runs/` SQLite state, or live agent sessions during `prepare-agents`.
