## MODIFIED Requirements

### Requirement: Overview guide table enumerates every catalog entry
`docs/getting-started/system-skills-overview.md` SHALL document every system skill listed under `[skills.*]` in `src/houmao/agents/assets/system_skills/catalog.toml` inside its "Packaged Skills" table (or an equivalently titled catalog table). Each row SHALL give the skill identifier, a brief "what it enables" summary, and the canonical `houmao-mgr` command routing the skill points at.

At minimum the guide SHALL surface the following skills currently declared in the catalog:

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

The guide MAY group these skills into concern-oriented subsections (for example "guided touring", "project, specialist, and credential authoring", "agent definition and instance management", "communication, gateway, and mailbox", "loop authoring and master-run control"), provided every catalog entry appears in exactly one subsection.

#### Scenario: Overview guide table tracks catalog membership
- **WHEN** a reader compares the overview guide catalog table to `catalog.toml`
- **THEN** every `[skills.<name>]` entry in the catalog has exactly one row in the guide
- **AND THEN** the guide does not list a skill that is not in the catalog

#### Scenario: Stable and v2 pairwise skills appear in the overview guide
- **WHEN** a reader opens the overview guide
- **THEN** the catalog table contains distinct rows for `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2`
- **AND THEN** the stable row describes the simpler restored pairwise run-control surface
- **AND THEN** the v2 row describes the enriched versioned pairwise workflow and distinguishes it from the stable pairwise skill

#### Scenario: Loop skills appear in the overview guide
- **WHEN** a reader opens the overview guide
- **THEN** the catalog table contains rows for `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, and `houmao-agent-loop-relay`
- **AND THEN** the "canonical CLI routing" column for each loop skill points the reader at the supported operating and authoring command paths actually shipped by the packaged skill assets

## ADDED Requirements

### Requirement: Overview guide auto-install description includes both pairwise variants when `user-control` includes both
The "Auto-Install vs Explicit Install" section of `docs/getting-started/system-skills-overview.md` SHALL explain that managed launch, managed join, and CLI-default installation all include both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2` whenever the current `user-control` set resolves both skills.

#### Scenario: Overview auto-install wording reflects both pairwise variants
- **WHEN** a reader inspects the overview guide's auto-install narrative or diagram
- **THEN** the guide includes both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2` wherever it expands the current `user-control` set
- **AND THEN** it does not imply that only one pairwise variant is auto-installed when the catalog includes both
