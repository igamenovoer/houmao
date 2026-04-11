## MODIFIED Requirements

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
- `houmao-agent-loop-pairwise-v2`
- `houmao-agent-loop-generic`

The "What it enables" column SHALL describe each skill in operator-facing language and SHALL avoid claiming a skill exists when it is not present in the catalog.

#### Scenario: README row count matches catalog size
- **WHEN** a reader compares the README system-skills table to `src/houmao/agents/assets/system_skills/catalog.toml`
- **THEN** every `[skills.<name>]` block in the catalog has exactly one corresponding row in the README table
- **AND THEN** the README table contains no row for a skill that is not declared in the catalog

#### Scenario: Pairwise v2 skill is surfaced in the README catalog
- **WHEN** a reader opens the README "System Skills" subsection
- **THEN** the table contains a distinct row for `houmao-agent-loop-pairwise-v2`
- **AND THEN** the row describes the skill as the versioned enriched pairwise workflow that remains manual-invocation-only

#### Scenario: Loop skills are surfaced in the README catalog
- **WHEN** a reader opens the README "System Skills" subsection
- **THEN** the table contains distinct rows for `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, and `houmao-agent-loop-generic`
- **AND THEN** each row briefly explains the loop-authoring and master-run control purpose of the skill

#### Scenario: Generic loop planner replaces relay-only row
- **WHEN** a reader opens the README "System Skills" subsection after the generic replacement
- **THEN** the table contains `houmao-agent-loop-generic`
- **AND THEN** it does not contain `houmao-agent-loop-relay` as a current shipped skill

### Requirement: README user-control set enumeration includes pairwise-v2
The README paragraph that describes which skills the `user-control` set includes SHALL list `houmao-agent-loop-pairwise-v2` alongside the existing members (`houmao-project-mgr`, `houmao-specialist-mgr`, `houmao-credential-mgr`, `houmao-agent-definition`, `houmao-agent-loop-pairwise`, `houmao-agent-loop-generic`).

The README paragraph that describes which skills the `user-control` set includes SHALL NOT list `houmao-agent-loop-relay` after the generic replacement.

#### Scenario: Reader sees pairwise-v2 in the user-control set expansion
- **WHEN** a reader reads the README paragraph describing which skills compose the `user-control` set
- **THEN** the paragraph lists `houmao-agent-loop-pairwise-v2` as a member of the `user-control` set
- **AND THEN** the paragraph lists `houmao-agent-loop-generic` as the generic loop planner member of the `user-control` set
- **AND THEN** the total count of `user-control` members matches the `[sets.user-control].skills` array in `catalog.toml`

#### Scenario: Reader does not see relay loop planner in current user-control expansion
- **WHEN** a reader reads the README paragraph describing which skills compose the `user-control` set after the generic replacement
- **THEN** the paragraph does not list `houmao-agent-loop-relay` as a current member of the set

### Requirement: README system-skills narrative count tracks the catalog
The README SHALL NOT claim a fixed "twelve" or "eleven" system-skill count when the catalog contains a different number of skills. Any narrative sentence that states how many packaged system skills ship SHALL state the number that matches the current catalog, and any sentence describing auto-install defaults SHALL reference the resolved `[auto_install] managed_launch_sets`, `managed_join_sets`, and `cli_default_sets` contents rather than a frozen count.

#### Scenario: README narrative skill count matches the catalog
- **WHEN** a reader reads the README sentence that introduces how many packaged Houmao system skills ship
- **THEN** that sentence references the same count as the current `src/houmao/agents/assets/system_skills/catalog.toml`
- **AND THEN** the sentence does not contradict the row count of the README system-skills table

#### Scenario: README auto-install wording tracks the resolved sets
- **WHEN** a reader reads the README paragraph describing which skills `agents launch` and `agents join` auto-install
- **THEN** the described set expansions match the `managed_launch_sets` and `managed_join_sets` entries in `catalog.toml`
- **AND THEN** the paragraph includes `houmao-agent-loop-generic` through `user-control` when the catalog includes it
- **AND THEN** the paragraph does not assert that `houmao-agent-loop-pairwise` or `houmao-agent-loop-generic` are left out of managed-home auto-install unless the catalog has been updated to reflect that policy
