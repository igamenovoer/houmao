## ADDED Requirements

### Requirement: Loop authoring guide presents pro and lite as current choices
The loop authoring guide SHALL present both `houmao-agent-loop-pro` and `houmao-agent-loop-lite` as current maintained Houmao loop skills.

The guide SHALL describe pro as the schema-rich generated-execplan path with generated contracts, harnesses, generated skills, agent bindings, workspace readiness, validation, launch, and run control.

The guide SHALL describe lite as the Markdown/direct-SQL path with required communication templates, required generated skills, direct SQLite state, no JSON schemas, no Jinja2, no generated harness, and no generated docs layer.

The guide SHALL NOT present retired pairwise or generic loop packages as current choices.

#### Scenario: Reader chooses lite for a simple Markdown loop
- **WHEN** a reader wants a lightweight loop with Markdown contracts and direct SQLite bookkeeping
- **THEN** the guide directs them to `houmao-agent-loop-lite`
- **AND THEN** it explains that lite does not generate harness or docs directories

#### Scenario: Reader chooses pro for stronger generated validation
- **WHEN** a reader wants topology contracts, schema-typed mail, harness commands, or stronger generated validation
- **THEN** the guide directs them to `houmao-agent-loop-pro`
- **AND THEN** it does not route that work to lite
