## ADDED Requirements

### Requirement: Project-local skill packages use one canonical content-root entry per skill name
Project-local skill packages SHALL resolve through one canonical content-root entry per registered project skill name under `.houmao/content/skills/<name>`.

That canonical project skill entry MAY be either:

- a copied directory owned by the project overlay, or
- a symlink entry that targets one source directory outside or inside the overlay.

The catalog SHALL treat that canonical content-root entry as the authoritative project-local skill payload rather than treating `.houmao/agents/skills/` as a second canonical skill store.

#### Scenario: Canonical project skill payload lives under the content root
- **WHEN** project skill `notes` is registered
- **THEN** the authoritative project-local skill entry is `.houmao/content/skills/notes`
- **AND THEN** the project overlay does not require `.houmao/agents/skills/notes` to be a peer source-of-truth store

### Requirement: Compatibility skill projections are derived from canonical project skill entries
When a project overlay materializes compatibility or runtime-facing skill trees, those trees SHALL be derived from the canonical project skill entries under `.houmao/content/skills/`.

For project-local compatibility projection, `.houmao/agents/skills/<name>` SHALL be treated as derived projection state only.

Persisted project-local specialist relationships to skills SHALL resolve by registered skill identity rather than by treating `.houmao/agents/skills/<name>` as the authoritative relationship key.

#### Scenario: Compatibility projection is rebuilt from canonical project skills
- **WHEN** project skill `notes` is registered at `.houmao/content/skills/notes`
- **AND WHEN** the project overlay materializes compatibility projection
- **THEN** `.houmao/agents/skills/notes` is produced from the canonical project skill entry
- **AND THEN** `.houmao/agents/skills/notes` is not treated as the primary project-local skill store

### Requirement: Project-structure migration remains explicit and centralized
Known legacy project-structure upgrades for catalog-backed project overlays SHALL run only through the supported `houmao-mgr project migrate` workflow.

Project catalog initialization, ordinary catalog load, and ordinary project-aware compatibility materialization SHALL NOT mutate legacy project structure in place as an implicit side effect.

Unsupported or unknown catalog-backed project state SHALL continue to fail explicitly rather than falling back to silent schema or layout upgrades.

#### Scenario: Ordinary catalog initialization does not perform project migration
- **WHEN** one selected project overlay contains a known legacy project structure that requires conversion
- **AND WHEN** ordinary catalog initialization or compatibility materialization runs outside `project migrate`
- **THEN** the flow does not rewrite the project structure implicitly
- **AND THEN** the operator is directed to the explicit project migration workflow
