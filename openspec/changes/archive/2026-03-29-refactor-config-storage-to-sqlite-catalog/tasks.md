## 1. Catalog Foundation

- [x] 1.1 Add project-overlay bootstrap support for `.houmao/catalog.sqlite`, managed `.houmao/content/` roots, and updated `project status` reporting.
- [x] 1.2 Define the initial SQLite schema, schema-version metadata, foreign keys, and integrity checks for specialists, roles, presets, setup profiles, skill packages, auth profiles, mailbox policies, and managed content references.
- [x] 1.3 Implement a project-local catalog repository/service seam that loads and persists domain objects without exposing raw storage layout to project-aware callers.
- [x] 1.4 Add stable read-oriented SQL inspection views or tables for the core catalog objects needed by advanced operators.

## 2. Managed Content Storage

- [x] 2.1 Introduce managed file-backed content storage for prompt blobs, auth file payloads, setup trees, and skill trees under the project overlay.
- [x] 2.2 Implement catalog-backed content reference types and resolution helpers so domain objects reference managed files and trees instead of path-bearing specialist metadata.
- [x] 2.3 Add validation and integrity checks for missing, duplicated, or orphaned managed content referenced by the catalog.

## 3. Legacy Import And Transition

- [x] 3.1 Implement one-way import from legacy project-local `.houmao/agents/` plus `.houmao/easy/` specialist metadata into the catalog and managed content store.
- [x] 3.2 Preserve the legacy tree as migration input or compatibility projection only, and make the catalog authoritative after successful import.
- [x] 3.3 Add migration-time validation and failure reporting for ambiguous or incomplete legacy specialist, auth, setup, skill, or preset state.

## 4. Project Easy Integration

- [x] 4.1 Refactor `project easy specialist create` to persist specialist semantics, auth selection, skill references, and prompt content through the catalog and managed content store.
- [x] 4.2 Refactor `project easy specialist list`, `get`, and `remove` to read and mutate catalog-backed specialist state while preserving shared managed content.
- [x] 4.3 Refactor `project easy instance launch` to resolve specialists from the catalog-backed domain layer and delegate launch using derived provider semantics.

## 5. Construction And Launch Resolution

- [x] 5.1 Refactor project-aware build and launch resolution to consume the catalog repository/service layer instead of traversing `.houmao/agents/` as authoritative project-local state.
- [x] 5.2 Update project-aware canonical parsing or domain assembly so downstream selector resolution and brain construction operate on storage-independent domain semantics for both filesystem-backed trees and catalog-backed overlays.
- [x] 5.3 Keep any required compatibility projection or materialization paths explicitly non-authoritative during the transition.

## 6. Verification And Documentation

- [x] 6.1 Add unit and integration coverage for project init/status bootstrap, catalog persistence, managed content references, legacy import, and project-easy specialist and instance flows.
- [x] 6.2 Add tests that exercise the advanced SQL inspection surface and catalog integrity behavior.
- [x] 6.3 Update operator and developer documentation to describe the new project-local storage model, migration expectations, managed content roots, and advanced SQL inspection workflow.
