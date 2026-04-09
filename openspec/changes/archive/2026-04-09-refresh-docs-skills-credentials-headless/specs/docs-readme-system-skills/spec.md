## ADDED Requirements

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
