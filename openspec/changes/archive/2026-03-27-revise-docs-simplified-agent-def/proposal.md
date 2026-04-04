## Why

The `simplify-agent-definition-model` change restructured the agent definition directory from a "brains-first" layout (`brains/brain-recipes/`, `brains/cli-configs/`, `brains/api-creds/`, `brains/tool-adapters/`, `blueprints/`) to a "role/tool-first" layout (`tools/<tool>/adapter.yaml`, `tools/<tool>/setups/`, `tools/<tool>/auth/`, `roles/<role>/presets/`, `skills/`). Getting-started docs and CLI reference docs were updated as part of that change, but the project README, several reference docs, and all LLM context files still reference the old model extensively — creating a confusing split where introductory docs describe the new layout while reference docs and the README still describe the obsolete one.

## What Changes

- Delete three obsolete reference docs that describe the old recipe/blueprint/brains model: `docs/reference/agents_brains.md`, `docs/reference/build-phase/recipes-and-adapters.md`, and `docs/reference/build-phase/brain-builder.md`. The getting-started docs (`agent-definitions.md`, `quickstart.md`, `overview.md`) are the canonical replacement.
- Rewrite the README's agent-definition directory section (approx lines 186–370) to document the new `tools/`/`roles/`/`skills/`/presets layout, self-contained with inline examples. Fix scattered old-term references in the README introduction sections.
- Update all four LLM context files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`) to reflect the new directory structure, terminology (`setup` instead of `config_profile`, `auth` instead of `credential_profile`), and path conventions.
- Fix old-path references in `docs/reference/houmao_server_agent_api_live_suite.md`.
- Update `mkdocs.yml` navigation to remove entries for deleted files and fix any surviving cross-references to deleted docs.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `docs-build-phase-reference`: Remove `brain-builder.md` and `recipes-and-adapters.md` from the build-phase reference section. The getting-started `overview.md` now covers the two-phase lifecycle, and the old recipe/adapter composition model no longer exists.
- `docs-stale-content-removal`: Remove `agents_brains.md` (the legacy component-library walkthrough) and update any surviving cross-references. The getting-started agent-definitions doc is the canonical reference for the simplified layout.
- `docs-site-structure`: Update `mkdocs.yml` navigation to drop the three deleted reference pages and ensure no dangling nav entries remain.

## Impact

- Affected files: `README.md`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `mkdocs.yml`, `docs/reference/agents_brains.md` (deleted), `docs/reference/build-phase/brain-builder.md` (deleted), `docs/reference/build-phase/recipes-and-adapters.md` (deleted), `docs/reference/houmao_server_agent_api_live_suite.md`.
- No runtime code changes — this is a docs-only change.
- No test changes expected, unless doc-build tests exist that reference the deleted files.
- External impact: GitHub Pages site will lose three reference pages; anyone with bookmarks to those pages will get 404s.
