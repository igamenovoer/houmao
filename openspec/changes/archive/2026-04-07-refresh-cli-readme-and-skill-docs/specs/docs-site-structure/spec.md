## ADDED Requirements

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
