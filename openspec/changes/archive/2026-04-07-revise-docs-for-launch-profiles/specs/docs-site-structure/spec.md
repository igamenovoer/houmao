## MODIFIED Requirements

### Requirement: Index pages link to all new documentation pages

The `docs/index.md` and `docs/reference/index.md` files SHALL include links to all new pages created in prior changes plus the new launch-profiles guide:

- `docs/reference/gateway/operations/mail-notifier.md`
- `docs/reference/agents/operations/project-aware-operations.md`
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
