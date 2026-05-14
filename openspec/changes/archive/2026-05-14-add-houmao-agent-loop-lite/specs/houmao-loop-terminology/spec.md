## ADDED Requirements

### Requirement: Loop terminology distinguishes pro and lite without reviving retired package names
Current Houmao loop terminology SHALL distinguish `pro loop` or `pro execplan` from `lite loop` or `lite execplan`.

`pro` terminology SHALL refer to schema-rich generated execplans with generated contracts, harnesses, generated skills, agent bindings, and validation-heavy operation.

`lite` terminology SHALL refer to Markdown/direct-SQL generated loop packages with required typed Markdown communication templates, required generated skills, and direct SQLite state access.

Retired pairwise and generic loop package names SHALL remain historical or legacy terms and SHALL NOT become current package choices through lite terminology.

#### Scenario: Current docs use lite terminology
- **WHEN** current docs describe the lightweight loop path
- **THEN** they use `houmao-agent-loop-lite`, `lite loop`, or `lite execplan`
- **AND THEN** they do not describe that path with retired pairwise or generic package names

#### Scenario: Current docs use pro terminology
- **WHEN** current docs describe schema-rich generated execplans with harness support
- **THEN** they use `houmao-agent-loop-pro`, `pro loop`, or `pro execplan`
- **AND THEN** they distinguish that path from lite
