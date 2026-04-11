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
- `houmao-agent-loop-generic`

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
- **THEN** the catalog table contains rows for `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, and `houmao-agent-loop-generic`
- **AND THEN** the "canonical CLI routing" column for each loop skill points the reader at the supported operating and authoring command paths actually shipped by the packaged skill assets

#### Scenario: Generic loop planner replaces relay-only row
- **WHEN** a reader opens the overview guide after the generic replacement
- **THEN** the catalog table contains `houmao-agent-loop-generic`
- **AND THEN** it does not contain `houmao-agent-loop-relay` as a current shipped skill

### Requirement: Overview guide narrative count matches the catalog
The overview guide narrative SHALL NOT state a frozen skill count (for example "twelve system skills" or "eleven auto-installed skills") that does not match the current `catalog.toml` entry count and the resolved `[auto_install]` set contents.

Where the guide references how many skills exist, how many are auto-installed by `agents launch` or `agents join`, or how many are installed by `system-skills install` when no `--set` or `--skill` is supplied, those numbers SHALL be computed from the current catalog rather than copied as literal text.

#### Scenario: Overview narrative stays consistent with the catalog
- **WHEN** a reader reads the overview guide paragraphs that introduce the packaged system skills
- **THEN** those paragraphs do not assert a total skill count that contradicts `catalog.toml`
- **AND THEN** they do not assert an auto-install skill count that contradicts the resolved `managed_launch_sets`, `managed_join_sets`, or `cli_default_sets` expansions

#### Scenario: Overview auto-install diagram tracks the catalog
- **WHEN** a reader inspects the "Auto-Install vs Explicit Install" section of the overview guide
- **THEN** the ASCII diagram, prose, and per-set expansion table reflect the current resolved contents of `managed_launch_sets`, `managed_join_sets`, and `cli_default_sets` in `catalog.toml`
- **AND THEN** the diagram includes `houmao-agent-loop-generic` through `user-control` when the catalog includes it
- **AND THEN** the diagram does not leave `houmao-agent-loop-pairwise` or `houmao-agent-loop-generic` out of the managed-launch auto-install column unless the catalog removes them from the `user-control` set
