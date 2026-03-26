## ADDED Requirements

### Requirement: Docs index provides canonical navigation

The `docs/index.md` file SHALL serve as the single entry point for all Houmao documentation. It SHALL contain a table of contents linking to every section: getting-started, reference (organized by phase and subsystem), and developer guides. It SHALL NOT reference CAO as a primary concept, demo packs, or migration guides.

#### Scenario: New reader navigates from index

- **WHEN** a reader opens `docs/index.md`
- **THEN** they find links to getting-started, reference, and developer sections with one-line descriptions of each subsection

#### Scenario: No CAO or demo references in index

- **WHEN** inspecting `docs/index.md` content
- **THEN** the file contains zero references to "CAO" as a primary workflow, zero references to `scripts/demo/`, and zero references to migration guides

### Requirement: Directory structure mirrors source packages

The `docs/` directory structure SHALL organize reference content by system phase and subsystem, mirroring the source package layout: `reference/cli/`, `reference/build-phase/`, `reference/run-phase/`, `reference/gateway/`, `reference/mailbox/`, `reference/tui-tracking/`, `reference/lifecycle/`, `reference/registry/`, `reference/terminal-record/`, and `reference/system-files/`.

#### Scenario: Each source subsystem has a docs counterpart

- **WHEN** listing directories under `docs/reference/`
- **THEN** there is a subdirectory (or file) for each major source package: cli, build-phase, run-phase, gateway, mailbox, tui-tracking, lifecycle, registry, terminal-record, system-files

#### Scenario: Getting-started section exists at top level

- **WHEN** listing directories under `docs/`
- **THEN** a `getting-started/` directory exists alongside `reference/` and `developer/`
