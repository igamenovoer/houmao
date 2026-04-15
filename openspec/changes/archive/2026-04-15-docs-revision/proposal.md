## Why

Two recent features (agent workspace unification, mail-notifier notification mode) updated reference docs but left `README.md` and key user-facing pages behind. Separately, `docs/index.md` remains a bare link dump that doesn't serve as a real landing page for installed users, and `DEVLEPMENT-SETUP.md` has a long-standing typo in its filename.

## What Changes

- **README.md**: Add `memory/` to the `.houmao/` overlay layout description; add `agents workspace` command rows to the `agents join` capabilities table; add a pointer to the Managed Agent Workspaces getting-started guide. No structural change — section order and Quick Start step numbering (0–6) remain exactly as they are.
- **docs/index.md**: Add a 2–3 sentence intro and a "where to start" decision table (installed user / from-source / contributor) above the existing link sections. Retain all current link content.
- **DEVLEPMENT-SETUP.md**: Rename to `DEVELOPMENT-SETUP.md` (fix the typo). No content change.
- **docs/getting-started/quickstart.md**: Add a short note at the top clarifying that the guide uses `pixi run` (from-source checkout) and that installed users can drop the `pixi run` prefix and call `houmao-mgr` directly.

## Capabilities

### New Capabilities

None. All changes are documentation updates reflecting existing code behavior.

### Modified Capabilities

- `readme-structure`: The spec currently describes a 6-step README (steps 0–5), but the README was updated to 7 steps (0–6) when "Drive with Your CLI Agent" was added as step 1 and the remaining steps were renumbered. The spec must be updated to match the current structure and to require that workspace-unification content (memory/ overlay entry, agents workspace command) appears in the README.
- `docs-site-structure`: The spec requires `docs/index.md` to serve as a navigation entry point but does not require an introductory paragraph or audience-oriented "where to start" navigation. Extend the spec to require both.

## Impact

- `README.md`: Content additions only (no structural change).
- `docs/index.md`: Content expansion only (no links removed).
- `DEVLEPMENT-SETUP.md`: File renamed; check for references in other markdown files.
- `docs/getting-started/quickstart.md`: One note added at the top.
- `openspec/specs/readme-structure/spec.md`: Step numbering and workspace content requirements updated.
- `openspec/specs/docs-site-structure/spec.md`: Landing-page and audience-navigation requirements added.
