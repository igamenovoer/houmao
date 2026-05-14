## ADDED Requirements

### Requirement: README skill table uses unified agent-definition row
The System Skills table in README.md SHALL list `houmao-agent-definition` with a description that includes low-level roles/recipes, explicit launch profiles, specialists, easy profiles, and ready-profile generation.

If the README still mentions `houmao-specialist-mgr`, that mention SHALL identify it as compatibility or migration guidance rather than as a primary separate row for current specialist management.

#### Scenario: README table names the ready-profile path
- **WHEN** the README System Skills table is inspected
- **THEN** the `houmao-agent-definition` row includes ready-profile generation or one-click agent profile preparation in its description
- **AND THEN** specialist/easy-profile authoring is not described as belonging only to a separate primary skill
