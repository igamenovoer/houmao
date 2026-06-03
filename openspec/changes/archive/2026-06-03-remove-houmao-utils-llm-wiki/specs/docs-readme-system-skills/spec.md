## MODIFIED Requirements

### Requirement: README system-skills table enumerates every catalog entry
The README "System Skills: Agent Self-Management" subsection SHALL document every system skill listed under `[skills.*]` in `src/houmao/agents/assets/system_skills/catalog.toml`.

At minimum the table SHALL include one row for each of the following skills currently shipped by the catalog:

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

The "What it enables" column SHALL describe each skill in operator-facing language and SHALL avoid claiming a skill exists when it is not present in the catalog.

The row for `houmao-agent-loop-pairwise-v3` SHALL describe it as the workspace-aware pairwise loop authoring and run-control skill, consistent with the canonical one-line description in `docs/getting-started/system-skills-overview.md`.

The row for `houmao-agent-loop-pairwise-v4` SHALL describe it as the template-driven workspace-aware pairwise loop skill for rich task-note contracts, strict generated document templates, role-local hard gates, and source-constraint coverage audits.

#### Scenario: README row count matches catalog size
- **WHEN** a reader compares the README system-skills table to `src/houmao/agents/assets/system_skills/catalog.toml`
- **THEN** every `[skills.<name>]` block in the catalog has exactly one corresponding row in the README table
- **AND THEN** the README table contains no row for a skill that is not declared in the catalog

#### Scenario: Workspace manager is surfaced in the README catalog
- **WHEN** a reader opens the README "System Skills" subsection
- **THEN** the table contains `houmao-utils-workspace-mgr`
- **AND THEN** the row describes the skill as a utility for planning and executing multi-agent workspace layouts before launch

## REMOVED Requirements

### Requirement: README system-skills table lists the LLM Wiki utility skill
**Reason**: The LLM Wiki utility skill is removed from Houmao's current packaged system-skill catalog.

**Migration**: Remove the README row and install examples for `houmao-utils-llm-wiki`.
