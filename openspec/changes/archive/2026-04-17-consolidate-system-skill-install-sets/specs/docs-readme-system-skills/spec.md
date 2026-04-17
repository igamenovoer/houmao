## MODIFIED Requirements

### Requirement: README default-install paragraph matches current system_skills.py defaults
The `README.md` paragraph that explains which skills `agents join` and `agents launch` auto-install by default into managed homes SHALL match the current set declared in `src/houmao/agents/system_skills.py` and the packaged catalog as of this change.

The README SHALL describe managed launch and managed join as resolving the `core` set.

The README SHALL describe omitted-selection external `houmao-mgr system-skills install` as resolving the `all` set.

When the auto-install set or the CLI-default external-install set changes during implementation discovery, the README SHALL be updated to match, and any divergence between the README paragraph and the current source SHALL be treated as a doc bug.

#### Scenario: README auto-install set agrees with current source
- **WHEN** a reader compares the README auto-install paragraph with the current system-skill defaults
- **THEN** the listed managed launch and managed join set is `core`
- **AND THEN** any skill that is added to or removed from `core` is reflected in the README

#### Scenario: README CLI-default install set agrees with current source
- **WHEN** a reader compares the README explanation of `system-skills install` defaults with the current system-skill defaults
- **THEN** the listed omitted-selection CLI default set is `all`
- **AND THEN** the README explains that `all` includes utility skills

### Requirement: README system-skills table enumerates every catalog entry
The README "System Skills: Agent Self-Management" subsection SHALL document every system skill listed under `[skills.*]` in `src/houmao/agents/assets/system_skills/catalog.toml`.

At minimum the table SHALL include one row for each of the following skills currently shipped by the catalog:

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

The "What it enables" column SHALL describe each skill in operator-facing language and SHALL avoid claiming a skill exists when it is not present in the catalog.

#### Scenario: README row count matches catalog size
- **WHEN** a reader compares the README system-skills table to `src/houmao/agents/assets/system_skills/catalog.toml`
- **THEN** every `[skills.<name>]` block in the catalog has exactly one corresponding row in the README table
- **AND THEN** the README table contains no row for a skill that is not declared in the catalog

#### Scenario: Workspace manager is surfaced in the README catalog
- **WHEN** a reader opens the README "System Skills" subsection
- **THEN** the table contains `houmao-utils-workspace-mgr`
- **AND THEN** the row describes the skill as a utility for planning and executing multi-agent workspace layouts before launch

## ADDED Requirements

### Requirement: README explains current core and all set surface
The README system-skills subsection SHALL explain that the current installable named sets are `core` and `all`.

The README SHALL explain that `core` is used for managed launch and join defaults, and `all` is used by `houmao-mgr system-skills install` when no `--skill-set` or `--skill` is supplied.

The README MAY organize skills as automation, control, and utils for readability, but SHALL NOT present those organization groups as installable set names.

#### Scenario: Reader sees current set names from README
- **WHEN** a reader scans the README system-skills subsection
- **THEN** they see `core` and `all` as the supported named set surface
- **AND THEN** they do not see removed granular set names presented as current installable sets

### Requirement: README system-skills table lists the workspace-manager utility skill
The README system-skills subsection SHALL list `houmao-utils-workspace-mgr` as one of the current packaged Houmao-owned system skills.

That catalog row or list entry SHALL describe `houmao-utils-workspace-mgr` as the utility skill for planning and executing multi-agent workspace layouts before launching agents.

The README SHALL distinguish `houmao-utils-workspace-mgr` from lifecycle skills by explaining that it prepares workspaces and launch-profile cwd changes but does not launch agents.

#### Scenario: Reader sees workspace manager in README
- **WHEN** a reader scans the README system-skills catalog table or list
- **THEN** they find `houmao-utils-workspace-mgr` with a one-line description
- **AND THEN** the entry describes workspace preparation rather than live managed-agent lifecycle operation

## REMOVED Requirements

### Requirement: README user-control set enumeration includes pairwise-v2
**Reason**: The README no longer documents `user-control` as a current installable set. `houmao-agent-loop-pairwise-v2` remains documented as a current packaged skill and is included through `core` and `all`.

**Migration**: Describe current set membership through `core` and `all`, and keep `houmao-agent-loop-pairwise-v2` in the catalog table.

#### Scenario: Pairwise v2 remains documented without user-control
- **WHEN** a reader scans the README system-skills subsection
- **THEN** they find `houmao-agent-loop-pairwise-v2` in the catalog table
- **AND THEN** README set guidance refers to `core` and `all`
