## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Index pages link to all new documentation pages

The `docs/index.md` and `docs/reference/index.md` files SHALL include links to all new pages created in prior changes plus the new launch-profiles guide:

- `docs/reference/gateway/operations/mail-notifier.md`
- `docs/reference/system-files/project-aware-operations.md`
- `docs/reference/mailbox/contracts/project-mailbox-skills.md`
- `docs/getting-started/easy-specialists.md`
- `docs/getting-started/launch-profiles.md`
- `docs/reference/build-phase/launch-policy.md`

Each link SHALL include a one-line description.

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
