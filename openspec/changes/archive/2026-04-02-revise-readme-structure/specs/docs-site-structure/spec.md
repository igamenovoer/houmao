## MODIFIED Requirements

### Requirement: Docs index provides canonical navigation

The `docs/index.md` file SHALL serve as the single entry point for all Houmao documentation. It SHALL contain a table of contents linking to every section: getting-started, reference (organized by phase and subsystem), and developer guides. It SHALL NOT reference CAO as a primary concept, demo packs, migration guides, or deleted pages (`agents_brains.md`, `brain-builder.md`, `recipes-and-adapters.md`). Links to the deleted build-phase pages SHALL be removed; the build-phase section SHALL list `launch-overrides.md` and `launch-policy.md`.

The docs index SHALL include a note indicating that the project README provides the recommended starting point for new users, linking back to the repository README or GitHub Pages landing page.

#### Scenario: New reader navigates from index

- **WHEN** a reader opens `docs/index.md`
- **THEN** they find links to getting-started, reference, and developer sections with one-line descriptions of each subsection

#### Scenario: No CAO or demo references in index

- **WHEN** inspecting `docs/index.md` content
- **THEN** the file contains zero references to "CAO" as a primary workflow, zero references to `scripts/demo/`, and zero references to migration guides

#### Scenario: No references to deleted pages in index

- **WHEN** inspecting `docs/index.md` content
- **THEN** the file contains zero references to `agents_brains.md`, `brain-builder.md`, or `recipes-and-adapters.md`

#### Scenario: Docs index acknowledges README as entry point

- **WHEN** a reader opens `docs/index.md`
- **THEN** they find a note or link indicating that the project README is the recommended starting point for new users
