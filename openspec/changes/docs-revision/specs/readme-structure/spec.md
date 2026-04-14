## MODIFIED Requirements

### Requirement: README section ordering follows specialist-first onboarding

The README SHALL present sections in this order: title/intro, What It Is, Quick Start (steps 0–6), Typical Use Cases, System Skills, Subsystems, Runnable Demos, CLI Entry Points, Full Documentation, Development. The Quick Start steps SHALL be numbered 0 through 6.

#### Scenario: Reader scans the Quick Start headings
- **WHEN** a reader opens README.md and scans section headings
- **THEN** they see step 0 (Install & Prerequisites), step 1 (Drive with Your CLI Agent), step 2 (Initialize a Project), step 3 (Create Specialists & Launch Agents), step 4 (Agent Loop), step 5 (Adopt an Existing Session), step 6 (Full Recipes and Launch Profiles)

### Requirement: project init is step 2

Step 2 SHALL introduce `houmao-mgr project init` and explain the `.houmao/` overlay. The overlay description SHALL include `memory/` as one of the listed subdirectories, described as the per-agent workspace root that holds memo files and scratch/persist lanes.

#### Scenario: User initializes a project
- **WHEN** a user reads step 2 and runs `houmao-mgr project init`
- **THEN** they understand the `.houmao/` directory is the project scaffold and can proceed to create specialists

#### Scenario: memory/ appears in the overlay layout description
- **WHEN** a reader scans the overlay layout bullet list in step 2
- **THEN** `memory/` appears as an entry alongside agents/, content/, mailbox/, catalog.sqlite, and houmao-config.toml

## ADDED Requirements

### Requirement: Drive with Your CLI Agent is step 1

Step 1 SHALL be titled "Drive with Your CLI Agent (Recommended)" and SHALL present the skill-driven path as the primary recommended entry point. It SHALL instruct the user to run `houmao-mgr system-skills install --tool <tool>` to install system skills into the project-local tool home, then start their agent from the same directory and invoke the `houmao-touring` skill. A note SHALL state that the remaining steps below show the manual CLI equivalents for reference.

#### Scenario: User follows step 1
- **WHEN** a user reads step 1 and installs system skills then starts their agent
- **THEN** they know to invoke `houmao-touring` for a guided walkthrough and understand the rest of the Quick Start is a manual reference

#### Scenario: Step 1 is clearly positioned as recommended
- **WHEN** a reader scans the Quick Start section headings
- **THEN** step 1 carries a "(Recommended)" qualifier that distinguishes it from the manual steps that follow

### Requirement: agents join capabilities table mentions agents workspace

The capabilities table in step 5 (Adopt an Existing Session) SHALL include at least one row describing `houmao-mgr agents workspace` commands, covering workspace path inspection and memo file operations.

#### Scenario: Reader sees workspace commands in join capabilities table
- **WHEN** a reader scans the capabilities table in step 5
- **THEN** they find a row for workspace inspection or memo operations that references `houmao-mgr agents workspace`
