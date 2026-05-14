## ADDED Requirements

### Requirement: README system-skill inventory lists lite alongside pro
The README system-skill inventory SHALL list `houmao-agent-loop-lite` as a current packaged Houmao system skill.

The README loop narrative SHALL describe `houmao-agent-loop-pro` and `houmao-agent-loop-lite` as separate current loop paths.

The README SHALL describe lite as the lightweight Markdown/direct-SQL loop path with required generated skills and communication templates.

The README SHALL continue to identify retired pairwise and generic loop packages only as retired or legacy material when mentioned.

#### Scenario: README names both current loop skills
- **WHEN** a reader scans the README system-skill inventory
- **THEN** they see `houmao-agent-loop-pro`
- **AND THEN** they see `houmao-agent-loop-lite`
- **AND THEN** retired loop package names are not presented as current installable choices

#### Scenario: README explains lite in one sentence
- **WHEN** a reader checks the README row for `houmao-agent-loop-lite`
- **THEN** the row describes Markdown contracts, typed communication templates, generated skills, and direct SQLite state
