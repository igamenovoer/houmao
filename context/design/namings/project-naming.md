# Project Naming

## Approved Name

The repository-facing project and distribution name is `Houmao`.

## Scope

This rename covers branding, packaging metadata, contributor-facing docs, and active guidance.
It does not rename the Python import root `gig_agents`, the CAO launcher `gig-cao-server`, or the existing runtime subcommands.

## Rationale

- `Houmao` gives the project one public identity instead of leaving `gig-agents` as the lingering package/distribution brand.
- The repo can accept breaking changes, so a clean rename is preferable to compatibility aliases.
- Keeping `gig_agents` as the import root keeps the packaging change narrow and avoids an unnecessary downstream migration.

## Canonical Reader Guidance

- Project / distribution name: `Houmao`
- Primary runtime CLI: `houmao-cli`
- Python import root: `gig_agents`
- Runtime module path: `gig_agents.agents.realm_controller`

## Explicit Non-Goals

Do not broaden this naming work into lore-driven renames of subcommands, classes, env vars, or unrelated package paths unless a later change explicitly approves that scope.
