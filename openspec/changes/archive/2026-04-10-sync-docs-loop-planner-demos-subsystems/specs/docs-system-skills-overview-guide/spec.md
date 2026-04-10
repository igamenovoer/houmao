## MODIFIED Requirements

### Requirement: Overview guide table enumerates every catalog entry

`docs/getting-started/system-skills-overview.md` SHALL document every system skill listed under `[skills.*]` in `src/houmao/agents/assets/system_skills/catalog.toml` inside its "Packaged Skills" table (or an equivalently titled catalog table). Each row SHALL give the skill identifier, a brief "what it enables" summary, and the canonical `houmao-mgr` command routing the skill points at.

At minimum the guide SHALL surface the following skills currently declared in the catalog:

- `houmao-touring`
- `houmao-project-mgr`
- `houmao-specialist-mgr`
- `houmao-credential-mgr`
- `houmao-agent-definition`
- `houmao-loop-planner`
- `houmao-agent-instance`
- `houmao-agent-messaging`
- `houmao-agent-gateway`
- `houmao-mailbox-mgr`
- `houmao-agent-email-comms`
- `houmao-process-emails-via-gateway`
- `houmao-adv-usage-pattern`
- `houmao-agent-loop-pairwise`
- `houmao-agent-loop-relay`

The guide MAY group these skills into concern-oriented subsections (for example "guided touring", "project, specialist, and credential authoring", "agent definition and instance management", "communication, gateway, and mailbox", "loop authoring and master-run control"), provided every catalog entry appears in exactly one subsection.

#### Scenario: Overview guide table tracks catalog membership
- **WHEN** a reader compares the overview guide catalog table to `catalog.toml`
- **THEN** every `[skills.<name>]` entry in the catalog has exactly one row in the guide
- **AND THEN** the guide does not list a skill that is not in the catalog

#### Scenario: Loop-planner appears in the overview guide
- **WHEN** a reader opens the overview guide
- **THEN** the catalog table contains a row for `houmao-loop-planner` in the "Loop authoring and master-run control" concern group
- **AND THEN** the row describes it as the operator-owned loop-bundle planning and runtime-handoff skill that is manual-invocation-only
- **AND THEN** the row distinguishes it from `houmao-agent-loop-pairwise` and `houmao-agent-loop-relay` which are the live-run control skills

#### Scenario: Loop skills appear in the overview guide
- **WHEN** a reader opens the overview guide
- **THEN** the catalog table contains rows for `houmao-agent-loop-pairwise` and `houmao-agent-loop-relay`
- **AND THEN** the "canonical CLI routing" column for each loop skill points the reader at the supported operating and authoring command paths actually shipped by the packaged skill assets
