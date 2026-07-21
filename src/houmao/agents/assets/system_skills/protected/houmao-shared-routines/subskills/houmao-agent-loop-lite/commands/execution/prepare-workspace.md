# Prepare Workspace

## Read First

- `../reference/markdown-contract-defaults.md`
- `../reference/platform-boundaries.md`
- `../reference/system-input-questions.md`

## Inputs

Require:
- `<loop-dir>`
- `execplan/manifest.md`
- prepared agent/profile facts when workspace setup is required

Use when present:
- `execplan/specs/workspace.md`
- `execplan/agents/bindings.md`

## Actions

1. If no workspace contract is present and manifest records no workspace need, report no workspace setup required.
2. When standard Houmao workspace setup is required, route planning, creation, validation, or summaries through `<public-entrypoint>->houmao-shared-routines->utils-workspace-mgr`.
3. Use prepared agent names and profile facts from `prepare-agents`.
4. Verify manual workspace evidence only when the execplan permits custom operator-owned setup.
5. Report planned, created, validated, summarized, missing, inconsistent, and custom/manual facts.

## Constraints

- Do not install skills, create specialists, launch agents, bind mailboxes, or call `prepare-agents`.
- Do not use legacy workspace-manager `execute` wording.
