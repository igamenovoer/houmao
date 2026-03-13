# Project Naming

## Approved Name

The repository-facing project and distribution name is `Houmao`.

## Scope

This rename covers branding, packaging metadata, contributor-facing docs, active guidance, the Python import root, and the CAO launcher CLI.
It does not rename the existing runtime subcommands.

## Rationale

- `Houmao` gives the project one public identity instead of leaving historical names in user-facing surfaces.
- The repo can accept breaking changes, so a clean rename is preferable to compatibility aliases.
- Renaming the import root and launcher CLI removes the last user-visible split between package, module, and command names.

## Canonical Reader Guidance

- Project / distribution name: `Houmao`
- Primary runtime CLI: `houmao-cli`
- CAO launcher CLI: `houmao-cao-server`
- Python import root: `houmao`
- Runtime module path: `houmao.agents.realm_controller`

## Explicit Non-Goals

Do not broaden this naming work into lore-driven renames of subcommands, classes, env vars, or unrelated package paths unless a later change explicitly approves that scope.
