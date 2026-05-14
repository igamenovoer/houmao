## ADDED Requirements

### Requirement: System-skills overview lists the lite loop skill
The getting-started system-skills overview guide SHALL list `houmao-agent-loop-lite` as one of the currently shipped packaged Houmao-owned system skills.

The guide SHALL describe `houmao-agent-loop-lite` as the lightweight Markdown/direct-SQL loop skill for generated skills, required typed Markdown templates, and direct SQLite state.

The guide SHALL distinguish `houmao-agent-loop-lite` from `houmao-agent-loop-pro`.

When the guide explains default install selections, it SHALL account for both current loop skills in the `core` and `all` sets.

#### Scenario: Overview table includes lite
- **WHEN** a reader opens the system-skills overview guide
- **THEN** the packaged skills table contains exactly one row for `houmao-agent-loop-lite`
- **AND THEN** the row describes lite as the no-harness Markdown/direct-SQL loop skill

#### Scenario: Overview distinguishes lite from pro
- **WHEN** a reader compares the loop skill rows in the overview guide
- **THEN** the pro row describes schema-rich generated execplans and harness-backed workflows
- **AND THEN** the lite row describes Markdown templates, generated skills, and direct SQLite state
