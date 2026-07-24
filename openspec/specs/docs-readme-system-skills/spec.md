# docs-readme-system-skills Specification

## Purpose
Define README requirements for documenting Houmao system skills and keeping top-level usage examples accurate.
## Requirements
### Requirement: README accuracy pass for recent refactors

The `README.md` SHALL be reviewed for accuracy against the current codebase. Any stale command examples, flag names, or descriptions introduced by recent refactors SHALL be corrected.

#### Scenario: README command examples match current CLI

- **WHEN** a reader copies a command example from the README
- **THEN** the command uses current flag names and does not fail with unrecognized options

### Requirement: README mentions the managed prompt header in the join/launch outcome

The `README.md` "What You Get After Joining" section (or the equivalent section that summarizes the operator-facing capabilities of a managed agent) SHALL include one short note explaining that managed launches and joins prepend a Houmao-owned prompt header by default, and SHALL link to the new managed prompt header reference page (`docs/reference/run-phase/managed-prompt-header.md`).

The note SHALL state that the header is opt-out via `--no-managed-header` on the launch surfaces and is persisted in stored launch profiles, deferring the full explanation to the linked reference page.

#### Scenario: Reader notices the managed prompt header from the README

- **WHEN** a reader scans the README "What You Get After Joining" section
- **THEN** they find one short note explaining that managed launches prepend a Houmao-owned prompt header by default
- **AND THEN** the note links to `docs/reference/run-phase/managed-prompt-header.md`
- **AND THEN** the note states that the header is opt-out via `--no-managed-header`

### Requirement: README CLI Entry Points table reflects `houmao-mgr --version`

The `README.md` CLI Entry Points table (or the equivalent paragraph that introduces `houmao-mgr`) SHALL note the existence of the `houmao-mgr --version` flag, either as a dedicated row, a footnote on the `houmao-mgr` row, or an inline mention immediately following the table.

The note SHALL state that `houmao-mgr --version` prints the packaged Houmao version and exits successfully without requiring a subcommand.

#### Scenario: Reader can find `--version` from the README CLI entry-points coverage

- **WHEN** a reader scans the README CLI Entry Points section
- **THEN** they see a mention of `houmao-mgr --version`
- **AND THEN** the mention explains what the flag prints and that it does not require a subcommand

### Requirement: README links the system-skills overview narrative guide

The `README.md` system-skills subsection SHALL link to the new narrative guide at `docs/getting-started/system-skills-overview.md` so that readers who want more than a catalog row can reach the walkthrough in one click.

The link SHALL be presented alongside the existing link to `docs/reference/cli/system-skills.md` rather than replacing it. Catalog → narrative → reference SHALL be the documented progression.

#### Scenario: Reader can navigate from the README catalog to the narrative overview

- **WHEN** a reader scans the README system-skills subsection
- **THEN** they find a link to `docs/getting-started/system-skills-overview.md`
- **AND THEN** they also find the existing link to `docs/reference/cli/system-skills.md`
- **AND THEN** the README presents catalog, narrative, and reference as the three layers of system-skills coverage

### Requirement: README does not contain a Current Status stability paragraph

The `README.md` file SHALL NOT contain a "Current Status" section (or any equivalently titled leading paragraph) that frames the `houmao-mgr` plus `houmao-server` operator surface as unstable, actively churning, or still stabilizing.

The opening content above the "Project Introduction" section SHALL jump directly from the project tagline to the introductory material without a separate status-disclaimer paragraph.

#### Scenario: Reader opens README without a misleading stability warning

- **WHEN** a reader opens `README.md` and reads from the top
- **THEN** there is no "Current Status" heading or section
- **AND THEN** there is no leading paragraph that tells the reader the operator interface is unstable or still stabilizing

#### Scenario: README does not describe `houmao-mgr` plus `houmao-server` as stabilizing

- **WHEN** searching `README.md` content above the "Project Introduction" section
- **THEN** the text does not claim that the operator interface is stabilizing, unstable, or likely to change

### Requirement: README Runnable Demos section lists all maintained demos

The README "Runnable Demos" section SHALL list every maintained demo directory under `scripts/demo/` that has a runner script and a README. At minimum the section SHALL include:

- `minimal-agent-launch/`
- `single-agent-mail-wakeup/`
- `single-agent-gateway-wakeup-headless/`
- `shared-tui-tracking-demo-pack/`

Historical directories under `scripts/demo/legacy/` MAY be omitted from the README but SHALL NOT be presented as maintained.

#### Scenario: Reader discovers all maintained demos from the README
- **WHEN** a reader reads the README "Runnable Demos" section
- **THEN** they find entries for `minimal-agent-launch/`, `single-agent-mail-wakeup/`, `single-agent-gateway-wakeup-headless/`, and `shared-tui-tracking-demo-pack/`
- **AND THEN** each entry includes a brief description and a runner command or link

### Requirement: README Subsystems at a Glance includes passive-server

The README "Subsystems at a Glance" table SHALL include a row for the passive-server subsystem with a link to `docs/reference/cli/houmao-passive-server.md`.

#### Scenario: Reader discovers the passive-server from the subsystems table
- **WHEN** a reader scans the README "Subsystems at a Glance" table
- **THEN** they find a row for the passive-server with a brief description and a link to its reference page

### Requirement: README CLI Entry Points documents the credentials family

The README "CLI Entry Points" subsection SHALL either list `houmao-mgr credentials` as a supported command family or otherwise visibly point readers at the dedicated credential-management surface before routing them into the full `docs/reference/cli/houmao-mgr.md` reference.

#### Scenario: Operator discovers credentials from the README entry point view
- **WHEN** an operator reads the README "CLI Entry Points" table
- **THEN** the page either shows `houmao-mgr credentials` in the table or surfaces it in a neighboring paragraph with a cross-link to the CLI reference section
- **AND THEN** the reader is not forced to read the narrower `project` examples to discover that a first-class credential-management surface exists

### Requirement: README surfaces internals graph as a discoverable command group

The `README.md` CLI Entry Points section SHALL include a discoverable reference to `houmao-mgr internals graph` — either as a note on the `houmao-mgr` row or as a separate paragraph. The reference SHALL state that `internals graph` provides loop-plan graph analysis and packet validation tooling.

#### Scenario: Reader discovers internals graph from the README

- **WHEN** a reader scans the README CLI Entry Points section
- **THEN** they find a reference to `houmao-mgr internals graph` with a brief description of its purpose
- **AND THEN** they are not required to read source code or run `houmao-mgr --help` to discover this surface

### Requirement: README distinguishes Skills CLI install from Houmao system-skills install

The README system-skill guidance SHALL present `npx skills add https://github.com/igamenovoer/houmao-skills` as the recommended install path when `npx` is available and the target machine has internet access. It SHALL explain that the repository root contains the released skills, the unqualified URL selects the latest stable release, and a `#vX.Y.Z` Git fragment selects the skills matching a specific `houmao-mgr` release.

The README SHALL present `houmao-mgr system-skills install` as the preferred path when `npx` is unavailable, internet access is unavailable, the user is working from an installed Houmao package, or the user needs customization such as named sets, subset skills, explicit homes, symlink/copy projection, or retired-skill cleanup.

The README SHALL point the external Skills CLI at the `houmao-skills` repository root rather than at an individual skill path, so the user can choose the released skill or skills to install.

#### Scenario: Reader sees the recommended internet path
- **WHEN** a reader scans the README's agent-driven setup guidance
- **THEN** they see an `npx skills add` command pointed at the root of the dedicated `houmao-skills` repository
- **AND THEN** the surrounding text qualifies that path as recommended when `npx` and internet access are available

#### Scenario: Reader selects a matching released skill version
- **WHEN** a reader needs skills for a specific `houmao-mgr` release
- **THEN** the README shows or explains a `houmao-skills#vX.Y.Z` source
- **AND THEN** the Git tag matches the Houmao release tag

#### Scenario: Reader sees when to use Houmao installer
- **WHEN** a reader needs offline, package-local, selected-set, selected-skill, explicit-home, symlink/copy, or cleanup behavior
- **THEN** the README routes them to `houmao-mgr system-skills install`
- **AND THEN** the README does not imply that the external Skills CLI owns Houmao-specific projection or cleanup behavior

### Requirement: README introduces the three-skill public surface
The README System Skills subsection SHALL present `houmao-admin-welcome`, `houmao-admin-entrypoint`, and `houmao-agent-entrypoint` as the complete public Houmao system-skill surface.

It SHALL describe protected routines as nested implementation, SHALL avoid a long flat routine table, and SHALL link to the System Skills Overview for the audience matrix and command-family detail.

#### Scenario: Reader scans the README system-skills section
- **WHEN** a reader wants the shortest public-surface explanation
- **THEN** the README identifies the welcome, admin execution, and managed-agent execution roles
- **AND THEN** it does not present protected logical ids as peer installable skills

### Requirement: README quick start begins with the admin welcome
The skill-driven quick start SHALL install the admin pack into the user's CLI-agent home and SHALL make `$houmao-admin-welcome start-guided-tour` the recommended first-use prompt.

The README SHALL explain that welcome is read-only and hands concrete work to `$houmao-admin-entrypoint ...`. It SHALL NOT recommend `$houmao-touring` as a current invocation.

#### Scenario: First-time user follows quick start
- **WHEN** the user completes system-skill installation for an external home
- **THEN** the next prompt invokes `houmao-admin-welcome`
- **AND THEN** the README shows the admin entrypoint as the execution owner

### Requirement: README distinguishes external and managed pack defaults
The README SHALL state that explicit external-home installation defaults to the admin pack, while managed launch, rebuild, relaunch, and join default to the agent pack.

It SHALL state that the admin welcome and entrypoint install atomically, no default installs both actors, and `houmao-auto-system-prompt` remains separate managed bootstrap content.

#### Scenario: Reader compares two homes
- **WHEN** a reader compares a human-operated CLI-agent home with a Houmao-managed home
- **THEN** the README identifies the admin pack for the first and the agent pack for the second
- **AND THEN** it does not describe `core`, `extensions`, or `all` as current selectors

### Requirement: README examples use public entrypoint invocations
System-skill examples SHALL begin with one of the three public skill names.

The README MAY name important protected routines when explaining ownership, but SHALL label them as nested routes and SHALL not use a protected id as a top-level `$skill` prompt. Help examples SHALL remain read-only and role-appropriate.

#### Scenario: README mentions agent-definition behavior
- **WHEN** the README explains specialist or profile authoring
- **THEN** it starts the executable example from `$houmao-admin-entrypoint`
- **AND THEN** it may identify protected `houmao-agent-definition` as the nested owner

### Requirement: README system-skill inventory matches the static public root
The README system-skills section SHALL list `houmao-admin-welcome`, `houmao-admin-entrypoint`, `houmao-agent-entrypoint`, `houmao-shared-routines`, `houmao-agent-loop-pro`, and `houmao-agent-loop-lite` exactly once as current standalone skills.

It SHALL explain that the sixteen ordinary routines are selected below shared routines through actor entrypoints or direct advanced invocation. It SHALL NOT list those children as top-level installed peers.

#### Scenario: README inventory is checked against packaged assets
- **WHEN** documentation validation compares README names with `system_skills/public/*/SKILL.md`
- **THEN** both inventories contain the same six names
- **AND THEN** no old protected-mount or flat low-level skill is advertised as a current root

### Requirement: README provides complete static installation examples
The README SHALL show the recommended Houmao admin-pack install, the managed agent-pack default, copy-paste directory lists, Skills CLI all-skills discovery, and explicit actor-specific Skills CLI selections.

Every example SHALL include shared routines and both loops when an actor entrypoint depends on them. The README SHALL state that Houmao's manager owns pack receipts while Skills CLI performs ordinary independent skill installation.

#### Scenario: User copies the admin skills manually
- **WHEN** a reader follows the README copy-paste admin example
- **THEN** the example copies all five admin-pack roots
- **AND THEN** the admin entrypoint has its shared and loop siblings

### Requirement: README preserves welcome and direct advanced routes
The README SHALL recommend `$houmao-admin-welcome` for first-use orientation, `$houmao-admin-entrypoint` for normal human operations, `$houmao-agent-entrypoint` for managed self, `$houmao-shared-routines` for advanced direct ordinary routines, and the two loop skills for explicit manual loop work.

#### Scenario: Advanced reader wants direct inspection
- **WHEN** a reader wants to bypass actor-entrypoint route selection
- **THEN** the README shows direct shared-routines invocation
- **AND THEN** it explains that target, identity, and runtime validation remain active
