## ADDED Requirements

### Requirement: Easy profiles manage registered and private skill overlays
`houmao-mgr project easy profile create` and `houmao-mgr project easy profile set` SHALL support storing profile-owned skill overlays without mutating the referenced source specialist.

The easy-profile surface SHALL accept repeatable `--add-registered-skill <name>` options. Each registered skill name SHALL reference an existing project skill registration by name and SHALL NOT create, import, copy, or symlink a new project skill registration.

The easy-profile surface SHALL accept repeatable `--remove-registered-skill <name>` options on `set`. Removing a registered skill SHALL remove only that easy-profile-owned reference and SHALL NOT remove the project skill registration.

The easy-profile surface SHALL accept repeatable `--add-private-skill <path>` options. Each private skill path SHALL identify a directory containing `SKILL.md`, SHALL derive its installed skill name from that directory name, and SHALL be stored with copy mode.

The easy-profile surface SHALL accept repeatable `--add-private-skill-symlink <path>` options. Each private skill path SHALL identify a directory containing `SKILL.md`, SHALL derive its installed skill name from that directory name, and SHALL be stored with symlink mode.

The easy-profile surface SHALL accept repeatable `--remove-private-skill <path>` options on `set`. Removing a private skill SHALL remove only the matching easy-profile-owned private skill reference and SHALL NOT mutate the referenced source directory.

Adding and removing the same registered skill name or the same normalized private skill path in one command SHALL fail clearly before mutating profile state.

Adding the same private installed skill name more than once in a single easy profile SHALL fail clearly before mutating profile state.

#### Scenario: Easy profile create stores registered and private skill overlays
- **WHEN** project skill `llm-wiki` is registered
- **AND WHEN** `/repo/profile-skills/audit/SKILL.md` exists
- **AND WHEN** an operator runs `houmao-mgr project easy profile create --name reviewer-a --specialist reviewer --add-registered-skill llm-wiki --add-private-skill /repo/profile-skills/audit`
- **THEN** easy profile `reviewer-a` stores registered skill ref `llm-wiki`
- **AND THEN** it stores private skill `audit` with source path `/repo/profile-skills/audit` and mode `copy`
- **AND THEN** project skill `audit` is not added to the project skill registry

#### Scenario: Easy profile set patches private symlink skill
- **WHEN** easy profile `reviewer-a` exists
- **AND WHEN** `/repo/profile-skills/live-tools/SKILL.md` exists
- **AND WHEN** an operator runs `houmao-mgr project easy profile set --name reviewer-a --add-private-skill-symlink /repo/profile-skills/live-tools`
- **THEN** easy profile `reviewer-a` stores private skill `live-tools` with mode `symlink`
- **AND THEN** project skill `live-tools` is not added to the project skill registry

#### Scenario: Easy profile rejects unknown registered skill
- **WHEN** project skill `unknown-skill` is not registered
- **AND WHEN** an operator runs `houmao-mgr project easy profile create --name reviewer-a --specialist reviewer --add-registered-skill unknown-skill`
- **THEN** the command fails clearly before mutating profile state
- **AND THEN** it tells the operator that `unknown-skill` is not a registered project skill

### Requirement: Easy profile inspection and projection report skill overlays
`houmao-mgr project easy profile get --name <profile>` SHALL report stored registered skill refs and private skill refs as part of the profile defaults.

`houmao-mgr project easy profile list` SHALL include enough structured skill-overlay summary data for operators to see that a profile contributes additional skills.

The projected `.houmao/agents/launch-profiles/<profile>.yaml` file for an easy profile SHALL render registered skill refs separately from private skill refs. Private skill refs SHALL include installed name, source path, and mode.

#### Scenario: Easy profile get reports registered and private skill overlays
- **WHEN** easy profile `reviewer-a` stores registered skill `llm-wiki`
- **AND WHEN** it stores private skill `audit` from `/repo/profile-skills/audit` with mode `copy`
- **AND WHEN** an operator runs `houmao-mgr project easy profile get --name reviewer-a`
- **THEN** the output reports registered skill ref `llm-wiki`
- **AND THEN** it reports private skill `audit`, its source path, and mode `copy`

#### Scenario: Easy profile projection renders skill overlays
- **WHEN** easy profile `reviewer-a` stores registered skill `llm-wiki`
- **AND WHEN** it stores private skill `audit` from `/repo/profile-skills/audit` with mode `symlink`
- **THEN** `.houmao/agents/launch-profiles/reviewer-a.yaml` contains a launch-profile skills block with registered `llm-wiki`
- **AND THEN** that file contains private skill `audit` with source path `/repo/profile-skills/audit` and mode `symlink`
