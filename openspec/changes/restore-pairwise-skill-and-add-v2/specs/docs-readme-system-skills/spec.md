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
- `houmao-agent-loop-relay`

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
- **THEN** the table contains distinct rows for `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, and `houmao-agent-loop-relay`
- **AND THEN** each row briefly explains the loop-authoring and master-run control purpose of the skill

### Requirement: README user-control set enumeration includes pairwise-v2
The README paragraph that describes which skills the `user-control` set includes SHALL list `houmao-agent-loop-pairwise-v2` alongside the existing members (`houmao-project-mgr`, `houmao-specialist-mgr`, `houmao-credential-mgr`, `houmao-agent-definition`, `houmao-agent-loop-pairwise`, `houmao-agent-loop-relay`).

#### Scenario: Reader sees pairwise-v2 in the user-control set expansion
- **WHEN** a reader reads the README paragraph describing which skills compose the `user-control` set
- **THEN** the paragraph lists `houmao-agent-loop-pairwise-v2` as a member of the `user-control` set
- **AND THEN** the total count of `user-control` members matches the `[sets.user-control].skills` array in `catalog.toml`

## ADDED Requirements

### Requirement: README auto-install wording includes both pairwise variants when `user-control` includes both
When the README describes the managed-home or CLI-default system-skill expansions, that wording SHALL include both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2` whenever the current packaged `user-control` set includes both.

#### Scenario: README auto-install wording tracks both pairwise variants
- **WHEN** a reader reads the README paragraph describing which skills `agents launch` and `agents join` auto-install
- **THEN** the described `user-control` expansion includes both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2` when the catalog includes both
- **AND THEN** the paragraph does not imply that only one pairwise variant is auto-installed through `user-control`
