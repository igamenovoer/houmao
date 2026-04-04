# docs-site-structure Specification

## Purpose
Define the documentation requirements for the top-level Houmao docs site structure.

## Requirements

### Requirement: Docs index provides canonical navigation

The `docs/index.md` file SHALL serve as the single entry point for all Houmao documentation. It SHALL contain a table of contents linking to every section: getting-started, reference (organized by phase and subsystem), and developer guides. It SHALL NOT reference CAO as a primary concept, demo packs, migration guides, or deleted pages (`agents_brains.md`, `brain-builder.md`, `recipes-and-adapters.md`). Links to the deleted build-phase pages SHALL be removed; the build-phase section SHALL list `launch-overrides.md` and `launch-policy.md`.

#### Scenario: New reader navigates from index

- **WHEN** a reader opens `docs/index.md`
- **THEN** they find links to getting-started, reference, and developer sections with one-line descriptions of each subsection

#### Scenario: No CAO or demo references in index

- **WHEN** inspecting `docs/index.md` content
- **THEN** the file contains zero references to "CAO" as a primary workflow, zero references to `scripts/demo/`, and zero references to migration guides

#### Scenario: No references to deleted pages in index

- **WHEN** inspecting `docs/index.md` content
- **THEN** the file contains zero references to `agents_brains.md`, `brain-builder.md`, or `recipes-and-adapters.md`

### Requirement: Directory structure mirrors source packages

The `docs/` directory structure SHALL organize reference content by system phase and subsystem, mirroring the source package layout: `reference/cli/`, `reference/build-phase/`, `reference/run-phase/`, `reference/gateway/`, `reference/mailbox/`, `reference/tui-tracking/`, `reference/lifecycle/`, `reference/registry/`, `reference/terminal-record/`, and `reference/system-files/`. The `reference/build-phase/` directory SHALL contain `launch-overrides.md` and `launch-policy.md` after the three deleted files are removed. The `mkdocs.yml` navigation SHALL reflect these deletions with no dangling entries.

#### Scenario: Each source subsystem has a docs counterpart

- **WHEN** listing directories under `docs/reference/`
- **THEN** there is a subdirectory (or file) for each major source package: cli, build-phase, run-phase, gateway, mailbox, tui-tracking, lifecycle, registry, terminal-record, system-files

#### Scenario: build-phase directory contains launch-overrides and launch-policy

- **WHEN** listing files under `docs/reference/build-phase/`
- **THEN** `launch-overrides.md` and `launch-policy.md` are present

#### Scenario: mkdocs.yml has no dangling nav entries

- **WHEN** parsing `mkdocs.yml` nav entries
- **THEN** no entry references `agents_brains.md`, `brain-builder.md`, or `recipes-and-adapters.md`

#### Scenario: Getting-started section exists at top level

- **WHEN** listing directories under `docs/`
- **THEN** a `getting-started/` directory exists alongside `reference/` and `developer/`

### Requirement: Index pages link to all new documentation pages

The `docs/index.md` and `docs/reference/index.md` files SHALL include links to all new pages created in this change:

- `docs/reference/gateway/operations/mail-notifier.md`
- `docs/reference/agents/operations/project-aware-operations.md`
- `docs/reference/mailbox/contracts/project-mailbox-skills.md`
- `docs/getting-started/easy-specialists.md`
- `docs/reference/build-phase/launch-policy.md`

Each link SHALL include a one-line description of the page content.

#### Scenario: New gateway mail-notifier page discoverable from index

- **WHEN** a reader navigates from `docs/index.md` to the gateway section
- **THEN** they find a link to `operations/mail-notifier.md` either directly or through the gateway index

#### Scenario: New build-phase launch-policy page discoverable from reference index

- **WHEN** a reader navigates to `docs/reference/index.md`
- **THEN** the build-phase section lists both `launch-overrides.md` and `launch-policy.md`

#### Scenario: New getting-started easy-specialists page listed in index

- **WHEN** a reader navigates to `docs/index.md`
- **THEN** the getting-started section lists the easy-specialists guide alongside overview, quickstart, and agent-definitions

### Requirement: Cross-references between new and existing pages verified

All cross-references between new pages and existing pages SHALL resolve correctly. Specifically:

- The easy-specialist guide SHALL link to the CLI reference for `project easy` commands.
- The gateway mail-notifier page SHALL link to the agents-gateway CLI page for command details.
- The project-aware operations page SHALL link to the getting-started agent-definitions page for overlay structure.
- The launch-policy page SHALL link to the launch-overrides page for the related override system.

#### Scenario: No broken cross-references in new pages

- **WHEN** a reader follows any cross-reference link in a new page
- **THEN** the target page exists and the link resolves correctly
