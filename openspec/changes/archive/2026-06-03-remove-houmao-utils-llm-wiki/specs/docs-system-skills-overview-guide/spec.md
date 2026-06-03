## ADDED Requirements

### Requirement: System-skills overview omits the removed LLM Wiki utility skill
The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL NOT describe `houmao-utils-llm-wiki` as a current packaged Houmao-owned system skill, installable named set member, managed-launch selector example, or canonical concern-routing target.

#### Scenario: Reader does not see removed LLM Wiki as current
- **WHEN** a reader opens `docs/getting-started/system-skills-overview.md`
- **THEN** the packaged skills table does not contain `houmao-utils-llm-wiki`
- **AND THEN** install examples do not use `houmao-utils-llm-wiki`

## MODIFIED Requirements

### Requirement: Overview guide table enumerates every catalog entry
`docs/getting-started/system-skills-overview.md` SHALL document every system skill listed under `[skills.*]` in `src/houmao/agents/assets/system_skills/catalog.toml` inside its "Packaged Skills" table or an equivalently titled catalog table. Each row SHALL give the skill identifier, a brief "what it enables" summary, and the canonical `houmao-mgr` command routing or utility workflow the skill points at.

At minimum the guide SHALL surface the following skills currently declared in the catalog:

- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`
- `houmao-adv-usage-pattern`
- `houmao-utils-workspace-mgr`
- `houmao-touring`
- `houmao-mailbox-mgr`
- `houmao-memory-mgr`
- `houmao-project-mgr`
- `houmao-specialist-mgr`
- `houmao-credential-mgr`
- `houmao-agent-definition`
- `houmao-agent-loop-pairwise`
- `houmao-agent-loop-pairwise-v2`
- `houmao-agent-loop-pairwise-v3`
- `houmao-agent-loop-pairwise-v4`
- `houmao-agent-loop-generic`
- `houmao-agent-instance`
- `houmao-agent-inspect`
- `houmao-agent-messaging`
- `houmao-agent-gateway`

The guide MAY group these skills into concern-oriented subsections such as automation, control, and utils, provided every catalog entry appears in exactly one subsection.

The row for `houmao-agent-loop-pairwise-v4` SHALL describe it as the template-driven workspace-aware pairwise loop skill for rich task-note contracts, strict generated document templates, role-local hard gates, and constraint coverage audits.

#### Scenario: Overview guide table tracks catalog membership
- **WHEN** a reader compares the overview guide catalog table to `catalog.toml`
- **THEN** every `[skills.<name>]` entry in the catalog has exactly one row in the guide
- **AND THEN** the guide does not list a skill that is not in the catalog

#### Scenario: Workspace manager appears in the overview guide
- **WHEN** a reader opens the overview guide
- **THEN** the catalog table contains a row for `houmao-utils-workspace-mgr`
- **AND THEN** the row describes workspace planning and execution before managed agents are launched

#### Scenario: Pairwise-v4 appears in the overview guide
- **WHEN** a reader opens the overview guide
- **THEN** the catalog table contains a row for `houmao-agent-loop-pairwise-v4`
- **AND THEN** the row describes template-driven pairwise planning with strict document templates and coverage audits

## REMOVED Requirements

### Requirement: System-skills overview guide includes the LLM Wiki utility skill
**Reason**: The LLM Wiki utility skill is removed from Houmao's current packaged system-skill catalog and docs should not advertise it.

**Migration**: Remove the LLM Wiki row, install examples, named-set prose, and concern-routing prose from the overview.
