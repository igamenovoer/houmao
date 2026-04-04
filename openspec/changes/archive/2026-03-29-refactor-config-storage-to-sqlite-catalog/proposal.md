## Why

Houmao's current project-local configuration storage encodes too much meaning in directory layout and path-bearing config files under `.houmao/agents/` and `.houmao/easy/`. That makes richer relationships hard to evolve safely, leaks storage details into logical models, and forces builders and project-aware runtime flows to reconstruct semantics from filesystem topology instead of a first-class catalog.

## What Changes

- Add a project-local SQLite-backed configuration catalog as the canonical semantic store for project overlays.
- Keep large text blobs and tree-shaped payloads such as system prompts, auth files, setup bundles, and skill packages file-backed under managed project-local content roots instead of moving all content into SQLite.
- Introduce catalog-owned domain identities and relationships for specialists, roles, presets, setup profiles, skill packages, auth profiles, mailbox policies, and related references so relationships are no longer encoded primarily by directory nesting.
- Refactor project-aware build, launch, and easy CLI flows to resolve project-local configuration through the catalog and managed content references rather than by traversing `.houmao/agents/` as the source of truth.
- Define a compatibility position for any remaining `.houmao/agents/` tree under project overlays so it becomes either a derived projection or a compatibility import surface rather than the canonical project-local storage contract. **BREAKING**
- Expose a stable advanced-operator inspection surface for the project-local catalog so knowledgeable users can inspect and intentionally manipulate catalog state with SQL-backed tools without relying on undocumented internal path relationships.

## Capabilities

### New Capabilities
- `project-config-catalog`: Canonical SQLite-backed project-local configuration catalog plus managed file-backed content references for large text and tree-shaped assets.

### Modified Capabilities
- `houmao-mgr-project-cli`: Project init, status, and project-aware defaults change from a tree-first overlay contract toward a catalog-backed project overlay contract.
- `houmao-mgr-project-easy-cli`: Easy specialist and instance workflows move from path-oriented local metadata and generated tree assumptions to catalog-backed specialist definitions and runtime resolution.
- `component-agent-construction`: Project-aware construction and selector resolution must consume canonical parsed/domain definitions that may come from the project catalog rather than only from a direct project-local `agents/` source tree.

## Impact

- Affected code includes `src/houmao/project/`, `src/houmao/srv_ctrl/commands/project.py`, `src/houmao/agents/definition_parser.py`, `src/houmao/agents/brain_builder.py`, `src/houmao/agents/native_launch_resolver.py`, and project-aware runtime/build loaders.
- Project-local overlay bootstrap, discovery, and persistence contracts change.
- Existing project-local storage paths and tests that assume `.houmao/agents/` or `.houmao/easy/specialists/*.toml` as canonical project state will need migration.
- New SQLite schema management, migration, integrity rules, and catalog/content reconciliation logic will be introduced.
