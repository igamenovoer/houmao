## MODIFIED Requirements

### Requirement: system-skills install is step 0

The Quick Start SHALL begin with a step 0 that instructs the user to run `houmao-mgr system-skills install --tool <tool>[,<tool>...]` before any other Houmao workflow. The step SHALL explain that without system skills, agents cannot self-manage through their native skill interface.

The step SHALL present omitted `--home` as the recommended default for project-local setup because each selected tool resolves its own env/default home. The step SHALL explain that `--home <home>` is valid only when installing for one tool and is intended for explicit external-home overrides.

When the README shows named system-skill set selection examples, it SHALL use `--skill-set <name>` rather than the removed `--set <name>` spelling.

#### Scenario: User follows step 0 with one or more tools
- **WHEN** a user reads step 0 and runs the install command with one tool or a comma-separated tool list
- **THEN** the system skills are installed into the resolved tool home or homes
- **AND THEN** subsequent agent launches gain self-management capabilities

#### Scenario: User understands explicit home override scope
- **WHEN** a user reads step 0 and wants to install into a specific external tool home
- **THEN** the README explains that they must run a single-tool install command with `--home <home>`
- **AND THEN** it does not imply that one `--home` value can be shared by comma-separated tools

#### Scenario: Skip note for join-only users
- **WHEN** a user only wants to try `agents join` without project setup
- **THEN** a visible note directs them to skip to step 4, explaining system skills are recommended but not required for the join path

### Requirement: Drive with Your CLI Agent is step 1

Step 1 SHALL be titled "Drive with Your CLI Agent (Recommended)" and SHALL present the skill-driven path as the primary recommended entry point. It SHALL instruct the user to run `houmao-mgr system-skills install --tool <tool>[,<tool>...]` to install system skills into the resolved project-local tool home or homes, then start their agent from the same directory and invoke the `houmao-touring` skill. A note SHALL state that the remaining steps show the manual CLI equivalents for reference.

Step 1 SHALL NOT present `--set` as the current named system-skill set selection flag.

#### Scenario: User follows step 1
- **WHEN** a user reads step 1 and installs system skills then starts their agent
- **THEN** they know to invoke `houmao-touring` for a guided walkthrough and understand the rest of the Quick Start is a manual reference

#### Scenario: Step 1 is clearly positioned as recommended
- **WHEN** a reader scans the Quick Start section headings
- **THEN** step 1 carries a "(Recommended)" qualifier that distinguishes it from the manual steps that follow
