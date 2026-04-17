## MODIFIED Requirements

### Requirement: Overview guide table enumerates every catalog entry
`docs/getting-started/system-skills-overview.md` SHALL document every system skill listed under `[skills.*]` in `src/houmao/agents/assets/system_skills/catalog.toml` inside its "Packaged Skills" table or an equivalently titled catalog table. Each row SHALL give the skill identifier, a brief "what it enables" summary, and the canonical `houmao-mgr` command routing or utility workflow the skill points at.

At minimum the guide SHALL surface the following skills currently declared in the catalog:

- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`
- `houmao-adv-usage-pattern`
- `houmao-utils-llm-wiki`
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
- `houmao-agent-loop-generic`
- `houmao-agent-instance`
- `houmao-agent-inspect`
- `houmao-agent-messaging`
- `houmao-agent-gateway`

The guide MAY group these skills into concern-oriented subsections such as automation, control, and utils, provided every catalog entry appears in exactly one subsection.

#### Scenario: Overview guide table tracks catalog membership
- **WHEN** a reader compares the overview guide catalog table to `catalog.toml`
- **THEN** every `[skills.<name>]` entry in the catalog has exactly one row in the guide
- **AND THEN** the guide does not list a skill that is not in the catalog

#### Scenario: Workspace manager appears in the overview guide
- **WHEN** a reader opens the overview guide
- **THEN** the catalog table contains a row for `houmao-utils-workspace-mgr`
- **AND THEN** the row describes workspace planning and execution before managed agents are launched

### Requirement: Overview guide narrative count matches the catalog
The overview guide narrative SHALL NOT state a frozen skill count that does not match the current `catalog.toml` entry count and the resolved `[auto_install]` set contents.

Where the guide references how many skills exist, how many are auto-installed by `agents launch` or `agents join`, or how many are installed by `system-skills install` when no `--skill-set` or `--skill` is supplied, those numbers SHALL be computed from the current catalog rather than copied as literal text.

The guide SHALL describe managed launch and join as resolving `core`, and omitted-selection CLI installs as resolving `all`.

#### Scenario: Overview narrative stays consistent with the catalog
- **WHEN** a reader reads the overview guide paragraphs that introduce the packaged system skills
- **THEN** those paragraphs do not assert a total skill count that contradicts `catalog.toml`
- **AND THEN** they do not assert an auto-install skill count that contradicts the resolved `managed_launch_sets`, `managed_join_sets`, or `cli_default_sets` expansions

#### Scenario: Overview auto-install wording tracks core and all
- **WHEN** a reader inspects the auto-install guidance in the overview guide
- **THEN** the guide states that managed launch and join use `core`
- **AND THEN** it states that omitted-selection `houmao-mgr system-skills install` uses `all`
- **AND THEN** it does not describe removed granular set names as current installable sets

## ADDED Requirements

### Requirement: System-skills overview guide explains organization groups and installable sets
The system-skills overview guide SHALL explain that automation, control, and utils are organization groups used for documentation readability.

The guide SHALL explain that the current installable named sets are only `core` and `all`.

The guide SHALL state that `core` is the managed launch/join default and `all` is the omitted-selection CLI install default.

#### Scenario: Reader understands groups versus sets
- **WHEN** a reader opens the system-skills overview guide
- **THEN** they can distinguish automation/control/utils organization groups from the installable `core` and `all` set names
- **AND THEN** install examples use `core`, `all`, or explicit skill names

### Requirement: System-skills overview guide includes the workspace manager utility skill
The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL list `houmao-utils-workspace-mgr` as one of the currently shipped packaged Houmao-owned system skills.

The guide SHALL describe `houmao-utils-workspace-mgr` as the utility skill for planning or executing multi-agent workspace layouts before agent launch, including in-repo and out-of-repo workspace flavors, worktrees, local-only shared repos, safe local-state symlink decisions, tracked-submodule materialization, launch-profile cwd updates, and optional memo seed augmentation.

The guide SHALL state that the workspace manager is part of the utility group, is included by `all`, and is not included by managed launch or managed join defaults unless explicitly selected.

#### Scenario: Reader sees workspace manager utility behavior
- **WHEN** a reader opens `docs/getting-started/system-skills-overview.md`
- **THEN** the guide lists `houmao-utils-workspace-mgr`
- **AND THEN** it describes the skill as workspace preparation guidance rather than an agent launch skill

## REMOVED Requirements

### Requirement: System-skills overview guide includes the packaged mailbox-admin skill and mailbox set distinction
**Reason**: The overview guide still documents `houmao-mailbox-mgr`, but it no longer documents `mailbox-core` and `mailbox-full` as current set names.

**Migration**: Describe mailbox skills under the automation/control organization narrative and use `core` or `all` for set-based install examples.

#### Scenario: Mailbox admin remains documented without mailbox sets
- **WHEN** a reader opens the overview guide
- **THEN** `houmao-mailbox-mgr` remains listed as a current packaged skill
- **AND THEN** `mailbox-core` and `mailbox-full` are not described as current installable set names

### Requirement: Overview guide auto-install description includes both pairwise variants when `user-control` includes both
**Reason**: `user-control` is no longer a current installable set name. Both pairwise variants remain in the catalog and are included through `core` and `all`.

**Migration**: Describe pairwise variants as current catalog skills and describe default installation through `core` and `all`.

#### Scenario: Pairwise variants remain documented without user-control
- **WHEN** a reader opens the overview guide
- **THEN** both `houmao-agent-loop-pairwise` and `houmao-agent-loop-pairwise-v2` remain listed as current packaged skills
- **AND THEN** default-install guidance refers to `core` and `all`
