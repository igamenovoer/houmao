## 1. Package the current Houmao-owned skill assets

- [x] 1.1 Move the current `houmao-*` skill trees into a neutral packaged runtime asset root under `src/houmao/agents/assets/` while keeping project starter assets separate.
- [x] 1.2 Add the packaged `catalog.toml` and matching `catalog.schema.json` that define the installable current skills, named skill sets, fixed auto-install set lists, and explicit schema version.
- [x] 1.3 Implement the shared system-skill installer and install-state tracking for Claude, Codex, and Gemini tool homes.
- [x] 1.4 Implement catalog loading that normalizes the packaged TOML payload, validates it against the packaged JSON Schema, and rejects unknown cross-references before any installation proceeds.

## 2. Integrate the shared installer into managed runtime flows

- [x] 2.1 Update managed brain construction to install the current Houmao-owned skill selection resolved from the catalog’s managed-launch set list through the shared installer instead of mailbox-only projection code.
- [x] 2.2 Update `houmao-mgr agents join` to use the shared installer and the catalog’s managed-join set list for default Houmao-owned skill installation while preserving the explicit opt-out behavior.
- [x] 2.3 Refactor mailbox-specific helper paths to delegate to the shared installer contract without changing the current visible mailbox skill paths.

## 3. Add the explicit operator CLI for external homes

- [x] 3.1 Add the top-level `houmao-mgr system-skills` command family and wire it into the native CLI tree.
- [x] 3.2 Implement `system-skills list` and `system-skills status` using the packaged current-skill catalog, named sets, and install-state data.
- [x] 3.3 Implement `system-skills install` with explicit tool-home targeting, repeatable set selection, and current-skill selection validation.

## 4. Update docs and verification coverage

- [x] 4.1 Update CLI and mailbox/runtime docs to describe the shared Houmao-owned system-skill installer and the new `houmao-mgr system-skills` workflow.
- [x] 4.2 Add or update tests for packaged asset discovery, JSON Schema validation, named set expansion, unknown-reference rejection, tool-native projection paths, install-state ownership behavior, internal auto-install set handling, and the new CLI commands.
