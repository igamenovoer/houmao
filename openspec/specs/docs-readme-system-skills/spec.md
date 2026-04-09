# docs-readme-system-skills Specification

## Purpose
Define README requirements for documenting Houmao system skills and keeping top-level usage examples accurate.
## Requirements
### Requirement: README usage section introduces system skills
The `README.md` usage section SHALL include a subsection introducing the system-skills surface. The subsection SHALL appear after the "Subsystems at a Glance" table and before the "Full Documentation" section.

The subsection SHALL explain that Houmao installs packaged skills into agent tool homes so that agents can drive management tasks through their native skill interface without requiring the operator to invoke `houmao-mgr` manually.

The subsection SHALL list the seven non-mailbox packaged skill families:
- `houmao-project-mgr` — project overlay lifecycle, project layout, and project-scoped launch-profile and easy-instance inspection routing
- `houmao-specialist-mgr` — specialist authoring plus specialist-scoped launch and stop entry
- `houmao-credential-mgr` — project-local credential management
- `houmao-agent-definition` — low-level role and preset definition management
- `houmao-agent-instance` — managed agent instance lifecycle
- `houmao-agent-messaging` — prompt, queue, raw-input, mailbox routing, and reset-context guidance for already-running managed agents
- `houmao-agent-gateway` — gateway lifecycle, gateway discovery, wakeups, and notifier guidance for attached managed agents

The subsection SHALL explain that `agents join` and `agents launch` auto-install the packaged user-control, agent-messaging, and agent-gateway skills into managed homes by default, which means the managed `user-control` install now includes `houmao-project-mgr`, `houmao-specialist-mgr`, `houmao-credential-mgr`, and `houmao-agent-definition`, while explicit `houmao-mgr system-skills install` into an external tool home can add the broader CLI-default skill selection that also includes `houmao-agent-instance`.

The subsection SHALL show a brief current `houmao-mgr system-skills install` example for explicit external tool homes that relies on the CLI-default selection by omitting both `--set` and `--skill`.

The subsection SHALL link to `docs/reference/cli/system-skills.md` for the full reference.

#### Scenario: Reader discovers system skills from the README

- **WHEN** a reader scans the README usage section
- **THEN** they find a subsection describing the system-skills surface
- **AND THEN** they see the seven non-mailbox packaged skill families listed with brief descriptions
- **AND THEN** they see that `houmao-project-mgr` is presented as the project lifecycle and layout skill

#### Scenario: Reader can distinguish managed auto-install from external CLI-default install

- **WHEN** a reader wants to understand which Houmao skills appear inside managed homes versus an explicit external tool home
- **THEN** the README explains that managed launch and join auto-install the user-control, messaging, and gateway skills
- **AND THEN** it explains that the managed `user-control` set now includes `houmao-project-mgr`
- **AND THEN** it explains that external `system-skills install` can add the broader CLI-default selection that also includes `houmao-agent-instance`

#### Scenario: Reader can install system skills into an external tool home with current CLI syntax

- **WHEN** a reader wants to prepare an external tool home with Houmao skills
- **THEN** the README shows a `houmao-mgr system-skills install` example with `--tool` and `--home` flags and no stale `--default` flag
- **AND THEN** the example links to the full reference for additional options

### Requirement: README accuracy pass for recent refactors

The `README.md` SHALL be reviewed for accuracy against the current codebase. Any stale command examples, flag names, or descriptions introduced by recent refactors SHALL be corrected.

#### Scenario: README command examples match current CLI

- **WHEN** a reader copies a command example from the README
- **THEN** the command uses current flag names and does not fail with unrecognized options

### Requirement: README skill catalog lists the unified email-comms skill

The `README.md` system-skills subsection SHALL list `houmao-agent-email-comms` as one of the packaged skill families, alongside the existing entries documented by the prior pass.

The catalog row SHALL describe `houmao-agent-email-comms` as the ordinary shared-mailbox operations skill that pairs with `houmao-process-emails-via-gateway` (which handles notifier-driven unread-mail rounds).

The README SHALL NOT continue to describe the pre-unification split mailbox skill names as the current packaged skills.

#### Scenario: Reader sees the unified email-comms skill in the README catalog

- **WHEN** a reader scans the README system-skills catalog table or list
- **THEN** they find a row for `houmao-agent-email-comms` with a one-line description
- **AND THEN** the row distinguishes ordinary mailbox operations from notifier-driven unread-mail rounds

#### Scenario: README skill catalog does not list pre-unification split skill names as current

- **WHEN** a reader greps the README system-skills subsection for the pre-unification split mailbox skill names
- **THEN** none of those names appear as current packaged skills

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

### Requirement: README default-install paragraph matches current system_skills.py defaults

The `README.md` paragraph that explains which skills `agents join` and `agents launch` auto-install by default into managed homes SHALL match the current set declared in `src/houmao/srv_ctrl/commands/system_skills.py` (and any companion `agents/system_skills.py` source) as of this change. The paragraph SHALL be reverified during implementation rather than reused verbatim from the prior pass.

When the auto-install set or the CLI-default external-install set changes during implementation discovery, the README SHALL be updated to match, and any divergence between the README paragraph and the current source SHALL be treated as a doc bug.

#### Scenario: README auto-install set agrees with current source

- **WHEN** a reader compares the README "auto-install" paragraph with the current `system_skills.py` defaults
- **THEN** the listed auto-install set matches the live source
- **AND THEN** any skill that was added to or removed from the auto-install set after the prior doc pass is reflected in the README

#### Scenario: README CLI-default install set agrees with current source

- **WHEN** a reader compares the README explanation of `system-skills install` defaults with the current `system_skills.py` defaults
- **THEN** the listed CLI-default set matches the live source

### Requirement: README links the system-skills overview narrative guide

The `README.md` system-skills subsection SHALL link to the new narrative guide at `docs/getting-started/system-skills-overview.md` so that readers who want more than a catalog row can reach the walkthrough in one click.

The link SHALL be presented alongside the existing link to `docs/reference/cli/system-skills.md` rather than replacing it. Catalog → narrative → reference SHALL be the documented progression.

#### Scenario: Reader can navigate from the README catalog to the narrative overview

- **WHEN** a reader scans the README system-skills subsection
- **THEN** they find a link to `docs/getting-started/system-skills-overview.md`
- **AND THEN** they also find the existing link to `docs/reference/cli/system-skills.md`
- **AND THEN** the README presents catalog, narrative, and reference as the three layers of system-skills coverage

### Requirement: README system-skills subsection lists the packaged mailbox-admin skill
The `README.md` system-skills subsection SHALL list `houmao-mailbox-mgr` as one of the current packaged skill families.

That catalog row or list entry SHALL describe `houmao-mailbox-mgr` as the mailbox-administration skill for mailbox root lifecycle, mailbox account lifecycle, structural mailbox inspection, and late managed-agent filesystem mailbox binding.

That subsection SHALL distinguish `houmao-mailbox-mgr` from `houmao-agent-email-comms` and `houmao-process-emails-via-gateway` by explaining that the new skill handles mailbox administration while the existing mailbox skills handle ordinary mailbox participation and notifier-driven unread-mail rounds.

#### Scenario: Reader sees the packaged mailbox-admin skill in the README catalog
- **WHEN** a reader scans the README system-skills catalog table or list
- **THEN** they find `houmao-mailbox-mgr` with a one-line description
- **AND THEN** the entry describes mailbox administration rather than ordinary mailbox operations

#### Scenario: README catalog distinguishes mailbox administration from mailbox participation
- **WHEN** a reader compares the README rows for `houmao-mailbox-mgr`, `houmao-agent-email-comms`, and `houmao-process-emails-via-gateway`
- **THEN** the README explains that `houmao-mailbox-mgr` owns mailbox administration
- **AND THEN** it keeps ordinary mailbox operations and notifier-driven unread-mail rounds on the existing mailbox worker skills

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

### Requirement: README system-skills subsection lists the touring skill
The `README.md` system-skills subsection SHALL list `houmao-touring` as one of the current packaged Houmao-owned system skills.

That catalog row or list entry SHALL describe `houmao-touring` as the manual guided-tour skill for first-time or re-orienting users.

The README SHALL explain that `houmao-touring` is a branching guided entrypoint that can orient the user across project setup, mailbox setup, specialist or profile authoring, live-agent operations, and lifecycle follow-up.

The README SHALL state that `houmao-touring` is manual-invocation-only rather than the default entrypoint for ordinary direct-operation requests.

#### Scenario: Reader sees the touring skill in the README catalog
- **WHEN** a reader scans the README system-skills catalog table or list
- **THEN** they find `houmao-touring` with a one-line description
- **AND THEN** the description presents it as a guided tour skill rather than as a direct-operation manager

#### Scenario: README describes touring as manual-only and branching
- **WHEN** a reader checks the `houmao-touring` entry in the README system-skills subsection
- **THEN** the README states that the skill is manual-invocation-only
- **AND THEN** it explains that the touring flow can branch across setup, launch, live operations, and lifecycle follow-up

### Requirement: README system-skills table enumerates every catalog entry

The README "System Skills: Agent Self-Management" subsection SHALL document every system skill listed under `[skills.*]` in `src/houmao/agents/assets/system_skills/catalog.toml`.

At minimum the table SHALL include one row for each of the following skills currently shipped by the catalog:

- `houmao-touring`
- `houmao-project-mgr`
- `houmao-specialist-mgr`
- `houmao-credential-mgr`
- `houmao-agent-definition`
- `houmao-agent-instance`
- `houmao-agent-messaging`
- `houmao-agent-gateway`
- `houmao-mailbox-mgr`
- `houmao-agent-email-comms`
- `houmao-process-emails-via-gateway`
- `houmao-adv-usage-pattern`
- `houmao-agent-loop-pairwise`
- `houmao-agent-loop-relay`

The "What it enables" column SHALL describe each skill in operator-facing language and SHALL avoid claiming a skill exists when it is not present in the catalog.

#### Scenario: README row count matches catalog size
- **WHEN** a reader compares the README system-skills table to `src/houmao/agents/assets/system_skills/catalog.toml`
- **THEN** every `[skills.<name>]` block in the catalog has exactly one corresponding row in the README table
- **AND THEN** the README table contains no row for a skill that is not declared in the catalog

#### Scenario: Loop skills are surfaced in the README catalog
- **WHEN** a reader opens the README "System Skills" subsection
- **THEN** the table contains distinct rows for `houmao-agent-loop-pairwise` and `houmao-agent-loop-relay`
- **AND THEN** each row briefly explains the loop-authoring and master-run control purpose of the skill

### Requirement: README system-skills narrative count tracks the catalog

The README SHALL NOT claim a fixed "twelve" or "eleven" system-skill count when the catalog contains a different number of skills. Any narrative sentence that states how many packaged system skills ship SHALL state the number that matches the current catalog, and any sentence describing auto-install defaults SHALL reference the resolved `[auto_install] managed_launch_sets`, `managed_join_sets`, and `cli_default_sets` contents rather than a frozen count.

#### Scenario: README narrative skill count matches the catalog
- **WHEN** a reader reads the README sentence that introduces how many packaged Houmao system skills ship
- **THEN** that sentence references the same count as the current `src/houmao/agents/assets/system_skills/catalog.toml`
- **AND THEN** the sentence does not contradict the row count of the README system-skills table

#### Scenario: README auto-install wording tracks the resolved sets
- **WHEN** a reader reads the README paragraph describing which skills `agents launch` and `agents join` auto-install
- **THEN** the described set expansions match the `managed_launch_sets` and `managed_join_sets` entries in `catalog.toml`
- **AND THEN** the paragraph does not assert that `houmao-agent-loop-pairwise` or `houmao-agent-loop-relay` are left out of managed-home auto-install unless the catalog has been updated to reflect that policy

### Requirement: README CLI Entry Points documents the credentials family

The README "CLI Entry Points" subsection SHALL either list `houmao-mgr credentials` as a supported command family or otherwise visibly point readers at the dedicated credential-management surface before routing them into the full `docs/reference/cli/houmao-mgr.md` reference.

#### Scenario: Operator discovers credentials from the README entry point view
- **WHEN** an operator reads the README "CLI Entry Points" table
- **THEN** the page either shows `houmao-mgr credentials` in the table or surfaces it in a neighboring paragraph with a cross-link to the CLI reference section
- **AND THEN** the reader is not forced to read the narrower `project easy` examples to discover that a first-class credential-management surface exists
