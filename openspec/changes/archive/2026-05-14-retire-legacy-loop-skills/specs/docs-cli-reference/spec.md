## ADDED Requirements

### Requirement: CLI reference documents pro as current loop skill
The CLI reference page for system skills SHALL describe `houmao-agent-loop-pro` as the current packaged loop skill.

The reference SHALL omit retired pairwise and generic loop package names from current inventory lists.

#### Scenario: Reader checks current system-skills inventory
- **WHEN** a reader checks the CLI reference for current packaged system skills
- **THEN** the loop inventory includes `houmao-agent-loop-pro`
- **AND THEN** retired loop package names are not listed as current installable skills

### Requirement: CLI reference documents retired cleanup when relevant
The CLI reference SHALL explain that known retired Houmao loop skill projections may be removed during current install or uninstall operations.

#### Scenario: Reader sees stale skill cleanup behavior
- **WHEN** a reader checks install or uninstall semantics
- **THEN** the CLI reference explains cleanup of known retired loop skill projections
