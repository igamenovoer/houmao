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

Prepare launchable Houmao project profiles, project skill registrations, and concrete participant facts from `<loop-dir>/execplan/` before workspace setup or launch.

## Read First

- [../../references/generated-contract-defaults.md](../../references/generated-contract-defaults.md)
- MUST READ: [../../references/runtime-mail-model.md](../../references/runtime-mail-model.md)
- [../../references/platform-boundaries.md](../../references/platform-boundaries.md)
- [../../references/system-input-questions.md](../../references/system-input-questions.md)

## Workflow

1. Require `<loop-dir>`, `<loop-dir>/execplan/manifest.toml`, `<loop-dir>/execplan/agents/`, and `<loop-dir>/execplan/skills/` (plus current `validate-execplan` evidence when available).
2. Resolve each participant's intended specialist, project profile, tool (`claude`, `codex`, `kimi`, `dsh`), qualified launch mode (`Claude: headless|tui`, `Codex: headless|service|tui`, `Kimi: headless|service|tui|web`, `DSH: headless|service|web`), credential, generated skills, `system_skills` pack policy (`--system-skill-pack` / `--system-skills-mode`), notifier prompt path, memo seed posture, and pending launch cwd policy.
3. Register loop-generated or project-local skill groups through maintained `houmao-mgr project skills` surfaces when project skill registration is needed.
4. Route persisted specialist and profile preparation through `houmao-shared-routines->houmao-agent-definition` (`create-agent-fast-forward`, `profiles`, `specialists`, or `launch-dossiers` only when explicitly required), attaching generated skills, prompt sources, notifier prompt sources, memo seeds, `--tool-params`, and `system_skills` pack settings without manually enumerating built-in Houmao system skills.
5. Flag unknown, missing, or tool-incompatible launch modes (`headless`, `service`, `tui`, `web`) as preparation blockers unless the operator explicitly supplies a documented manual raw launch profile.
6. Record prepared agent facts (agent id, specialist, profile, stable workspace agent name, tool, credential, launch mode, skill groups, `system_skills` posture, notifier prompt path, memo posture, launch cwd/pending workspace policy, and whether a matching live session already exists) and emit the report below without launching agents.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this procedure, its owning skill constraints, available references, and the user request, then execute the plan.

## Report

Report readiness (`ready`, `ready with warnings`, or `blocked`), prepared profile facts, registered `project skills` and `system_skills` pack posture, notifier prompt and memo posture, pending workspace-dependent mutations, blockers for `prepare-workspace`/`validate-loop`/`launch-agents`, and non-blocking warnings, ending with one summary row per participant:

| Agent | Participant | Launch mode | Credential | Skill groups | Workdir |
| --- | --- | --- | --- | --- | --- |
| `<agent-id or profile>` | `<participant or role>` | `headless`, `service`, `tui`, or `web` | `<credential or unknown>` | `<generated/project skill groups>` | `<launch cwd or pending workspace policy>` |

Mark missing or inconsistent cells `blocked` and detail each blocker above the table.

## Guardrails

- DO NOT call `prepare-workspace`, invoke `houmao-shared-routines->houmao-utils-workspace-mgr`, or create worktrees or workspace directories during `prepare-agents`.
- DO NOT prepare mailboxes, gateways, live memories, harness state, or run artifacts here; reserve pre-launch cross-checks for `validate-loop`.
- DO NOT launch live agents or send loop-start triggers from this command; use `launch-agents` and `start`.
- DO NOT reimplement specialist, profile, launch-dossier, or credential logic owned by `houmao-shared-routines->houmao-agent-definition`, or install event/tick skills into the wrong participant profile.
- DO NOT configure agents to sleep, poll, tail logs, or wait in-chat for loop progress.
