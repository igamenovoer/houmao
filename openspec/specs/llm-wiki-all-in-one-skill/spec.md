## Purpose
Define the all-in-one LLM Wiki skill's root schema file contract.

## Requirements

### Requirement: Root Schema File Uses README
The all-in-one LLM Wiki skill SHALL define `README.md` as the required wiki root schema and operating-contract file.

#### Scenario: Skill startup guidance names README
- **WHEN** an agent reads the all-in-one skill instructions
- **THEN** the instructions require reading `README.md` and `wiki/index.md` at session start

#### Scenario: Wiki root layout names README
- **WHEN** the skill documents the expected wiki root directory layout
- **THEN** the root schema file is documented as `README.md`

### Requirement: Scaffold Creates README Only
The scaffold helper SHALL create `README.md` for new wiki roots and SHALL NOT create or instruct users to edit `CLAUDE.md`.

#### Scenario: New wiki is scaffolded
- **WHEN** the scaffold helper initializes a wiki root
- **THEN** it writes the schema template to `README.md`
- **AND** its console output and scaffold log refer to `README.md`

### Requirement: Documentation Omits Claude-Specific Schema Name
The all-in-one skill documentation SHALL NOT mention `CLAUDE.md` in skill instructions, reference guides, workflow notes, or viewer deployment guidance.

#### Scenario: Documentation is searched for old schema name
- **WHEN** the all-in-one skill deliverable is searched for `CLAUDE.md`
- **THEN** no matches are found

### Requirement: No Legacy Compatibility Contract
The all-in-one LLM Wiki skill SHALL NOT define fallback behavior, migration behavior, or compatibility wording for `CLAUDE.md`.

#### Scenario: Wiki root schema expectations are described
- **WHEN** the skill describes valid wiki root files or troubleshooting for invalid wiki roots
- **THEN** it names `README.md` as the schema file
- **AND** it does not describe `CLAUDE.md` as an accepted alternative
