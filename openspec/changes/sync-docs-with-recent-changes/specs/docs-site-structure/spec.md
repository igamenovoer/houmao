## MODIFIED Requirements

### Requirement: Docs index provides canonical navigation

The `docs/index.md` file SHALL serve as the single entry point for all Houmao documentation. It SHALL contain a table of contents linking to every section: getting-started, reference (organized by phase and subsystem), developer guides, and examples. It SHALL NOT reference CAO as a primary concept, demo packs, migration guides, or deleted pages (`agents_brains.md`, `brain-builder.md`, `recipes-and-adapters.md`). Links to the deleted build-phase pages SHALL be removed; the build-phase section SHALL list `launch-overrides.md` and `launch-policy.md`.

#### Scenario: New reader navigates from index

- **WHEN** a reader opens `docs/index.md`
- **THEN** they find links to getting-started, reference, developer sections, and examples with one-line descriptions of each subsection

#### Scenario: Writer-team example discoverable from index

- **WHEN** a reader scans `docs/index.md`
- **THEN** they find a reference to the `examples/writer-team/` template with a brief description of the multi-agent loop example
