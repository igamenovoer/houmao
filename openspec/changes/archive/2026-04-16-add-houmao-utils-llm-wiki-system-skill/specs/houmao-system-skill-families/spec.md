## ADDED Requirements

### Requirement: Utility logical group is represented by an explicit named set
The packaged current system-skill catalog SHALL represent general utility skills through a `utils` named set.

The `utils` set SHALL include `houmao-utils-llm-wiki`.

The `utils` set SHALL be explicit-only and SHALL NOT be part of managed launch, managed join, or CLI-default installation selections.

#### Scenario: Operator lists logical skill groups
- **WHEN** an operator lists the packaged Houmao-owned system skills and named sets
- **THEN** the named sets include `utils`
- **AND THEN** `utils` contains `houmao-utils-llm-wiki`
- **AND THEN** the default-selection metadata does not include `utils`

#### Scenario: Explicit default installation omits utility group
- **WHEN** an operator installs system skills without `--skill-set` or `--skill`
- **THEN** the resolved CLI-default selection does not include `houmao-utils-llm-wiki`
