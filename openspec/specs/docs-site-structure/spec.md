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

The `docs/index.md` and `docs/reference/index.md` files SHALL include links to all new pages created in prior changes plus the new launch-profiles guide:

- `docs/reference/gateway/operations/mail-notifier.md`
- `docs/reference/system-files/project-aware-operations.md`
- `docs/reference/mailbox/contracts/project-mailbox-skills.md`
- `docs/getting-started/easy-specialists.md`
- `docs/getting-started/launch-profiles.md`
- `docs/reference/build-phase/launch-policy.md`

Each link SHALL include a one-line description of the page content.

The `mkdocs.yml` navigation SHALL list `docs/getting-started/launch-profiles.md` under the getting-started section so the page is discoverable through the published navigation, and SHALL contain no dangling entries for that page.

#### Scenario: New gateway mail-notifier page discoverable from index

- **WHEN** a reader navigates from `docs/index.md` to the gateway section
- **THEN** they find a link to `operations/mail-notifier.md` either directly or through the gateway index

#### Scenario: New build-phase launch-policy page discoverable from reference index

- **WHEN** a reader navigates to `docs/reference/index.md`
- **THEN** the build-phase section lists both `launch-overrides.md` and `launch-policy.md`

#### Scenario: New getting-started easy-specialists page listed in index

- **WHEN** a reader navigates to `docs/index.md`
- **THEN** the getting-started section lists the easy-specialists guide alongside overview, quickstart, and agent-definitions

#### Scenario: New launch-profiles guide listed in index and mkdocs nav

- **WHEN** a reader navigates to `docs/index.md`
- **THEN** the getting-started section lists the launch-profiles guide alongside overview, quickstart, agent-definitions, and easy-specialists
- **AND THEN** `mkdocs.yml` navigation includes a getting-started entry for `launch-profiles.md`
- **AND THEN** the mkdocs navigation has no dangling entry for that path

#### Scenario: Project-aware operations page linked from its new system-files home

- **WHEN** a reader navigates to `docs/reference/index.md` or `docs/index.md` and looks for project-aware operations guidance
- **THEN** the link points at `docs/reference/system-files/project-aware-operations.md`
- **AND THEN** no index entry points at the retired `docs/reference/agents/operations/project-aware-operations.md` path

### Requirement: Cross-references between new and existing pages verified

All cross-references between new pages and existing pages SHALL resolve correctly. Specifically:

- The easy-specialist guide SHALL link to the CLI reference for `project easy` commands and to the launch-profiles guide for the shared conceptual model.
- The launch-profiles guide SHALL link to the easy-specialists guide, the agent-definitions guide, the `houmao-mgr` CLI reference, and the build-phase launch-overrides reference.
- The agent-definitions guide SHALL link to the launch-profiles guide for the shared conceptual model.
- The quickstart SHALL link to the launch-profiles guide where it mentions `agents launch --launch-profile`.
- The launch-overrides reference SHALL link to the launch-profiles guide for the shared conceptual model.
- The launch-plan reference SHALL link to the launch-profiles guide for the shared conceptual model.
- The gateway mail-notifier page SHALL link to the agents-gateway CLI page for command details.
- The project-aware operations page SHALL link to the getting-started agent-definitions page for overlay structure.
- The launch-policy page SHALL link to the launch-overrides page for the related override system.

#### Scenario: No broken cross-references in new pages

- **WHEN** a reader follows any cross-reference link in a new page
- **THEN** the target page exists and the link resolves correctly

#### Scenario: Launch-profiles guide cross-links resolve

- **WHEN** a reader follows the cross-reference links from `docs/getting-started/launch-profiles.md`
- **THEN** the easy-specialists, agent-definitions, `houmao-mgr` CLI reference, and launch-overrides target pages exist and resolve

### Requirement: Index pages link the new managed prompt header reference and system-skills overview guide

The `docs/index.md` and `docs/reference/index.md` files SHALL include links to the two new pages introduced by this change:

- `docs/reference/run-phase/managed-prompt-header.md` — under the run-phase section of the reference index, alongside `launch-plan.md`, `session-lifecycle.md`, `backends.md`, and `role-injection.md`,
- `docs/getting-started/system-skills-overview.md` — under the getting-started section of `docs/index.md`, alongside the overview, quickstart, agent-definitions, easy-specialists, and launch-profiles entries.

Each link SHALL include a one-line description.

The `mkdocs.yml` navigation SHALL list both new pages under the appropriate section so they are reachable through the published navigation, and SHALL contain no dangling entries for those paths.

#### Scenario: Managed prompt header reference is linked from the reference index

- **WHEN** a reader navigates to `docs/reference/index.md`
- **THEN** the run-phase section lists `managed-prompt-header.md` alongside `launch-plan.md`, `session-lifecycle.md`, `backends.md`, and `role-injection.md`
- **AND THEN** the entry has a one-line description

#### Scenario: System-skills overview guide is linked from the docs index

- **WHEN** a reader navigates to `docs/index.md`
- **THEN** the getting-started section lists `system-skills-overview.md` alongside the existing getting-started entries
- **AND THEN** the entry has a one-line description

#### Scenario: mkdocs.yml has navigation entries for both new pages

- **WHEN** parsing `mkdocs.yml` nav entries
- **THEN** the run-phase nav contains an entry for `managed-prompt-header.md`
- **AND THEN** the getting-started nav contains an entry for `system-skills-overview.md`
- **AND THEN** the navigation has no dangling entries for either path

### Requirement: Cross-references between new pages and existing pages verified during this pass

The cross-references introduced by this change SHALL all resolve correctly. Specifically:

- The managed prompt header reference SHALL link to `docs/getting-started/launch-profiles.md`, `docs/reference/run-phase/role-injection.md`, and `docs/reference/cli/houmao-mgr.md`.
- The system-skills overview guide SHALL link to `docs/reference/cli/system-skills.md`, `docs/getting-started/easy-specialists.md`, `docs/getting-started/launch-profiles.md`, and the README system-skills subsection.
- The CLI reference for `houmao-mgr` SHALL link to `docs/reference/run-phase/managed-prompt-header.md` from the `--managed-header` flag coverage.
- The CLI reference for `system-skills` SHALL link to `docs/getting-started/system-skills-overview.md` from its introduction.
- The README system-skills subsection SHALL link to `docs/getting-started/system-skills-overview.md` alongside the existing link to `docs/reference/cli/system-skills.md`.

#### Scenario: No broken cross-references in pages introduced by this change

- **WHEN** a reader follows any cross-reference link in a page introduced or modified by this change
- **THEN** the target page exists and the link resolves correctly

### Requirement: Docs index lists the current top-level CLI reference pages

The `docs/index.md` file SHALL link to each of the following CLI reference pages from its CLI Surfaces section so the landing page matches the coverage already present in `docs/reference/index.md`:

- `docs/reference/cli/houmao-mgr.md`
- `docs/reference/cli/houmao-server.md`
- `docs/reference/cli/houmao-passive-server.md`
- `docs/reference/cli/system-skills.md`
- `docs/reference/cli/agents-gateway.md`
- `docs/reference/cli/agents-turn.md`
- `docs/reference/cli/agents-mail.md`
- `docs/reference/cli/agents-mailbox.md`
- `docs/reference/cli/admin-cleanup.md`

Each link SHALL include a one-line description.

#### Scenario: Reader finds the agents-gateway CLI reference from the landing page

- **WHEN** a reader opens `docs/index.md` and scans the CLI Surfaces section
- **THEN** the list includes a link to `docs/reference/cli/agents-gateway.md`
- **AND THEN** the link carries a one-line description

#### Scenario: Reader finds the admin-cleanup CLI reference from the landing page

- **WHEN** a reader opens `docs/index.md` and scans the CLI Surfaces section
- **THEN** the list includes a link to `docs/reference/cli/admin-cleanup.md`
- **AND THEN** the link carries a one-line description

#### Scenario: Reader finds the system-skills CLI reference from the landing page

- **WHEN** a reader opens `docs/index.md` and scans the CLI Surfaces section
- **THEN** the list includes a link to `docs/reference/cli/system-skills.md`
- **AND THEN** the link carries a one-line description

### Requirement: Docs index does not link to the retired runtime-managed agents subtree

The `docs/index.md` file SHALL NOT contain any link to `reference/agents/index.md`, `reference/agents/contracts/`, `reference/agents/operations/`, `reference/agents/internals/`, or `reference/agents/troubleshoot/`.

The `docs/reference/index.md` file SHALL NOT contain any link to the same retired subtree paths.

#### Scenario: No inbound link to reference/agents/index.md from the docs landing page

- **WHEN** inspecting `docs/index.md` for links
- **THEN** the file contains zero references to `reference/agents/index.md`

#### Scenario: No inbound link to reference/agents/* from the reference index page

- **WHEN** inspecting `docs/reference/index.md` for links
- **THEN** the file contains zero references to `agents/index.md`, `agents/contracts/`, `agents/operations/`, `agents/internals/`, or `agents/troubleshoot/`

### Requirement: Docs index opens with a brief intro and audience navigation

The `docs/index.md` file SHALL open with a short introductory block (2–3 sentences) describing what Houmao is and who the site is for (primarily installed users, with developer and contributor material available). Immediately after the intro, the file SHALL include a "where to start" table with at minimum three audience rows: installed user, from-source developer, and contributor. Each row SHALL name the audience and point to its recommended starting resource.

#### Scenario: Installed user lands on docs index
- **WHEN** an installed user opens `docs/index.md`
- **THEN** they read a 2–3 sentence description of what Houmao is before encountering any link list
- **AND THEN** they see a "where to start" entry pointing them toward the getting-started guides or skill-driven (`houmao-touring`) path

#### Scenario: From-source developer lands on docs index
- **WHEN** a developer working from a source checkout opens `docs/index.md`
- **THEN** the "where to start" table identifies them and points them to the quickstart guide

#### Scenario: Contributor lands on docs index
- **WHEN** a contributor opens `docs/index.md`
- **THEN** the "where to start" table identifies them and points them to CLAUDE.md or AGENTS.md

#### Scenario: Existing link sections are preserved
- **WHEN** a reader scrolls past the intro block
- **THEN** all previously existing Getting Started, Reference, and Developer Guides link sections are intact with no links removed
