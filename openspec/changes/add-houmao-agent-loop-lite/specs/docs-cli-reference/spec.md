## ADDED Requirements

### Requirement: CLI reference includes lite in current system-skill inventory
The CLI reference for system-skills SHALL list `houmao-agent-loop-lite` as a current catalog-known Houmao-owned system skill.

The reference SHALL include `houmao-agent-loop-lite` in the documented current `core` and `all` resolved sets when those sets are shown.

The reference SHALL preserve retired loop cleanup guidance for retired pairwise and generic package names without classifying `houmao-agent-loop-lite` as retired.

#### Scenario: CLI reference lists lite as current
- **WHEN** a reader opens the system-skills CLI reference
- **THEN** `houmao-agent-loop-lite` appears in the current skill inventory
- **AND THEN** it appears separately from retired loop cleanup names

#### Scenario: CLI reference set examples include lite
- **WHEN** the CLI reference shows resolved `core` or `all` system-skill sets
- **THEN** those examples include `houmao-agent-loop-lite`
- **AND THEN** they still include `houmao-agent-loop-pro`
