## ADDED Requirements

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
