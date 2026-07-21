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

# Prepare Workspace

## Read First

- `../reference/generated-contract-defaults.md`
- `../reference/platform-boundaries.md`
- `../reference/system-input-questions.md`

## Preconditions

- Generated execplan exists.
- Concrete agent/profile facts have been prepared or explicitly supplied.
- Operator wants workspace setup planned, created, validated, or summarized after agent preparation.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/execplan/manifest.toml`

Use when present:
- `<loop-dir>/execplan/specs/workspace/workspace.toml`;
- `<loop-dir>/execplan/agents/bindings.toml`;
- prepared concrete agent/profile facts from `prepare-agents`;
- generated participant specs;
- generated run artifact contracts;
- existing workspace-manager plan, validation report, summary, or workspace contract docs;
- operator-supplied manual workspace readiness evidence;
- operator approval for workspace creation.

## Actions

1. Validate the execplan shape before workspace preparation.
2. Read `execplan/manifest.toml` first.
3. If the manifest and generated docs record that no managed workspace is required, report that no workspace setup is required and stop.
4. Read `execplan/specs/workspace/workspace.toml`, `execplan/agents/bindings.toml`, prepared agent/profile facts, and related participant or run contracts when workspace setup or verification is required.
5. Extract workspace-manager inputs:
   - operation: `plan`, `create`, `validate`, or `summarize`;
   - workspace flavor, defaulting to `in-repo` when unspecified and supported;
   - task name, repo root, and workspace root policy;
   - concrete agent ids, workspace agent names, and project profile or explicit raw launch profile names prepared by `prepare-agents`;
   - launch cwd policy;
   - per-agent work roots, `shared-kb`, `owner-states`, per-agent `states`, shared resources, and read/write rules;
   - project-scope validation commands or documented safe project commands;
   - memo-seed and launch-profile adjustment posture.
6. Default to workspace-manager `plan` mode unless the user explicitly asks to create, validate, or summarize a workspace, or has approved a current plan for creation.
7. Treat legacy `execute` wording in older generated material or operator prompts as workspace-manager `create`, and report the normalized operation as `create`.
8. Use `<public-entrypoint>->houmao-shared-routines->utils-workspace-mgr` for supported workspace planning, creation, validation, or summaries.
9. Do not duplicate workspace-manager mechanics such as worktree creation, branch creation, local-state links, submodule materialization, shared repos, ignore-rule updates, memo-seed writes, or launch-profile cwd edits.
10. If the execplan selects a custom operator-owned workspace or the user supplies manual workspace readiness evidence, do not translate it into a standard workspace. Verify and report the custom or manual facts described by the execplan.
11. After planning, creation, validation, or summarization, compare available workspace facts with generated workspace contracts, generated agent bindings, and prepared agent/profile facts.

## Postconditions To Check

For standard created or validated workspaces, check applicable facts:
- workspace contract docs exist;
- per-agent worktrees exist;
- task-local `shared-kb/` exists when shared task knowledge is required;
- task-local `owner-states/<subdir>/...` exists when per-run task-owner bookkeeping is required;
- per-agent `states/` exists when agent-local bookkeeping is required;
- launch-profile cwd posture matches the selected workspace flavor when profile adjustment was requested;
- memo-seed files exist when requested;
- workspace-manager `validate` has passed, or missing/skipped/failed validation checks are reported with follow-up actions;
- no two agents share the same mutable worktree or private bookkeeping directory.

A workspace-manager `plan` report alone is not launch-ready evidence when managed workspace readiness is required.

## Tips

- When Git worktrees are required, read `../reference/git-worktree-readiness.md`.
- Treat Git worktree readiness as a multi-part contract: registered worktree, branch/cwd posture, submodules, required local-state links, project-scope validation commands, and recorded evidence.
- Keep standard worktree creation and repair routed through `<public-entrypoint>->houmao-shared-routines->utils-workspace-mgr` when it can represent the layout.

## Report

Report:
- operation used: `plan`, `create`, `validate`, `summarize`, or custom/manual verification;
- workspace flavor and root facts;
- no-workspace posture when the execplan records an intentional omission;
- manual workspace evidence accepted or rejected when supplied;
- prepared agent/profile facts used as workspace-manager inputs;
- planned facts;
- created facts;
- validated facts;
- summarized facts;
- ready facts;
- missing facts;
- inconsistent facts against `workspace.toml` or `bindings.toml`;
- custom/manual facts;
- skipped or failed validation checks;
- whether later execution stages may treat workspace readiness as complete.

## Constraints

- Do not install generated skills.
- Do not create or update specialists, profiles, mailboxes, gateways, memories, or live agents.
- Do not prepare mailbox, gateway, memory, inspection, or Houmao system-skill posture.
- Do not start loop work.
- Do not call or route to `prepare-agents`.
- Do not invent placeholder agent ids, workspace agent names, or profile names when they should come from `prepare-agents`.
- Do not create workspaces by hand when `<public-entrypoint>->houmao-shared-routines->utils-workspace-mgr` can represent the layout.
