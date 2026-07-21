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

# Prepare Agents

## Read First

- `../reference/generated-contract-defaults.md`
- MUST READ: `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`
- `../reference/system-input-questions.md`

## Preconditions

- Generated execplan exists.
- Operator wants launchable Houmao project profiles and prepared agent facts before workspace setup.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/execplan/manifest.toml`
- generated agent bindings under `<loop-dir>/execplan/agents/`
- generated skills under `<loop-dir>/execplan/skills/`

Use when present:
- generated profile definitions, prompt sources, notifier prompts, and memo seeds;
- generated workspace policy references that affect pending launch cwd or memo posture;
- current `validate-execplan` evidence.

## Actions

1. Read `execplan/manifest.toml` and generated agent bindings.
2. Resolve each participant's intended project profile, definition source, generated skills, notifier prompt path, memo seed posture, launch interface mode (`tui` or `headless`), and pending launch cwd posture.
3. Register loop-generated or loop-private skills through maintained project-skill surfaces when project-local skill registration is needed.
4. Route persisted agent/profile preparation through `<public-entrypoint>->houmao-shared-routines->agent-definition`:
   - `create-agent-fast-forward`: default when a participant may need both specialist and project profile preparation;
   - `profiles`: when the specialist already exists and only project profile material changes;
   - `specialists`: when only specialist material changes and no profile preparation is needed;
   - `launch-dossiers`: only when the execplan or operator explicitly requires launch dossier control.
5. Treat `houmao-mgr project ...` as the underlying surface owned by `<public-entrypoint>->houmao-shared-routines->agent-definition`, not as loop-local preparation logic.
6. Attach generated skills, definitions, notifier prompt sources, memo seed posture, and pending cwd/memo mutation intent to the prepared profile material.
7. Rely on Houmao managed-agent creation to preinstall Houmao system skills into agents; do not enumerate or manually bind ordinary Houmao support skills, including maintained mail support skills such as `<public-entrypoint>->houmao-shared-routines->process-emails-via-gateway`, in generated profile guidance.
8. Resolve and record prepared agent facts:
   - concrete agent ids;
   - specialist names;
   - project profile names, or raw launch profile names only when explicitly required;
   - stable workspace agent names;
   - selected tool and credential when reported by `<public-entrypoint>->houmao-shared-routines->agent-definition`;
   - launch interface mode, reporting whether the prepared profile is configured for TUI-backed or headless launch;
   - prompt or definition sources;
   - installed generated skills;
   - confirmation that Houmao system skills are preinstalled or will be preinstalled by managed-agent creation;
   - notifier prompt paths;
   - memo seed paths or pending memo posture;
   - launch cwd policy or pending launch cwd posture;
   - whether a matching live agent was observed without launching it.
9. Treat unknown, missing, or contradictory TUI/headless launch mode facts as preparation blockers unless the operator explicitly accepts a manual raw launch profile whose mode is documented outside the project-profile facts.
10. Report prepared agent/project-profile facts, installed generated skills, Houmao system-skill preinstall posture, notifier prompt posture, memo posture, pending workspace-dependent profile mutations, and blockers for `prepare-workspace`, `validate-loop`, or `launch-agents`.

## Report

Report:
- readiness result for agent preparation: ready, ready with warnings, or blocked;
- prepared agent/project-profile facts checked;
- installed generated skills and Houmao system-skill preinstall posture;
- notifier prompt posture;
- memo posture;
- pending workspace-dependent profile mutations;
- blockers for `prepare-workspace`, `validate-loop`, or `launch-agents`;
- warnings that do not block the next stage.

End the report with one Markdown summary table that has one row for every required participant or prepared concrete agent:

| Agent | Participant | Launch mode | Credential | Skill groups | Workdir |
| --- | --- | --- | --- | --- | --- |
| `<agent-id or profile>` | `<participant or role>` | `tui` or `headless` | `<credential display name or unknown>` | `<generated/private skill group names>` | `<launch cwd or pending workspace policy>` |

Use `blocked` in the relevant cell when a required fact is missing or inconsistent, then list the blocking detail above the table.

## Constraints

- Do not perform workspace preparation here: do not call `prepare-workspace`, run `<public-entrypoint>->houmao-shared-routines->utils-workspace-mgr`, create worktrees, or create workspace scaffolding.
- Do not prepare mailbox, gateway, memory, inspection, harness state, run artifacts, or broad runtime readiness here; use `validate-loop` for pre-launch readiness.
- Do not launch live agents as normal preparation behavior; use `launch-agents`.
- Do not start loop work from this page; use `start`.
- Do not reimplement specialist creation, project-profile mutation, launch-dossier mutation, credential defaulting, or launcher selection; route to `<public-entrypoint>->houmao-shared-routines->agent-definition`.
- Do not install generated event or tick skills into the wrong participant profile.
- Do not invent profiles when the execplan or user did not provide enough information; prefer project-profile creation/update before considering launch dossier editing.
- Do not prepare agents to sleep, poll, tail logs, or wait in-chat for loop progress; mail notifier prompts and operator prompts are the wakeup mechanism.
