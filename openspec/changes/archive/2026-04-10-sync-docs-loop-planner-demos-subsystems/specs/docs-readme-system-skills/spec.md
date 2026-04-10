## MODIFIED Requirements

### Requirement: README system-skills table enumerates every catalog entry

The README "System Skills: Agent Self-Management" subsection SHALL document every system skill listed under `[skills.*]` in `src/houmao/agents/assets/system_skills/catalog.toml`.

At minimum the table SHALL include one row for each of the following skills currently shipped by the catalog:

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

The "What it enables" column SHALL describe each skill in operator-facing language and SHALL avoid claiming a skill exists when it is not present in the catalog.

#### Scenario: README row count matches catalog size
- **WHEN** a reader compares the README system-skills table to `src/houmao/agents/assets/system_skills/catalog.toml`
- **THEN** every `[skills.<name>]` block in the catalog has exactly one corresponding row in the README table
- **AND THEN** the README table contains no row for a skill that is not declared in the catalog

#### Scenario: Loop-planner skill is surfaced in the README catalog
- **WHEN** a reader opens the README "System Skills" subsection
- **THEN** the table contains a distinct row for `houmao-loop-planner`
- **AND THEN** the row describes loop-planner as the operator-owned loop-bundle planning and runtime-handoff skill that is manual-invocation-only

#### Scenario: Loop skills are surfaced in the README catalog
- **WHEN** a reader opens the README "System Skills" subsection
- **THEN** the table contains distinct rows for `houmao-agent-loop-pairwise` and `houmao-agent-loop-relay`
- **AND THEN** each row briefly explains the loop-authoring and master-run control purpose of the skill

### Requirement: README user-control set enumeration includes loop-planner

The README paragraph that describes which skills the `user-control` set includes SHALL list `houmao-loop-planner` alongside the existing members (`houmao-project-mgr`, `houmao-specialist-mgr`, `houmao-credential-mgr`, `houmao-agent-definition`, `houmao-agent-loop-pairwise`, `houmao-agent-loop-relay`).

#### Scenario: Reader sees loop-planner in the user-control set expansion
- **WHEN** a reader reads the README paragraph describing which skills compose the `user-control` set
- **THEN** the paragraph lists `houmao-loop-planner` as a member of the `user-control` set
- **AND THEN** the total count of `user-control` members matches the `[sets.user-control].skills` array in `catalog.toml`

## ADDED Requirements

### Requirement: README Runnable Demos section lists all maintained demos

The README "Runnable Demos" section SHALL list every maintained demo directory under `scripts/demo/` that has a runner script and a README. At minimum the section SHALL include:

- `minimal-agent-launch/`
- `single-agent-mail-wakeup/`
- `single-agent-gateway-wakeup-headless/`
- `shared-tui-tracking-demo-pack/`

Historical directories under `scripts/demo/legacy/` MAY be omitted from the README but SHALL NOT be presented as maintained.

#### Scenario: Reader discovers all maintained demos from the README
- **WHEN** a reader reads the README "Runnable Demos" section
- **THEN** they find entries for `minimal-agent-launch/`, `single-agent-mail-wakeup/`, `single-agent-gateway-wakeup-headless/`, and `shared-tui-tracking-demo-pack/`
- **AND THEN** each entry includes a brief description and a runner command or link

### Requirement: README Subsystems at a Glance includes passive-server

The README "Subsystems at a Glance" table SHALL include a row for the passive-server subsystem with a link to `docs/reference/cli/houmao-passive-server.md`.

#### Scenario: Reader discovers the passive-server from the subsystems table
- **WHEN** a reader scans the README "Subsystems at a Glance" table
- **THEN** they find a row for the passive-server with a brief description and a link to its reference page
