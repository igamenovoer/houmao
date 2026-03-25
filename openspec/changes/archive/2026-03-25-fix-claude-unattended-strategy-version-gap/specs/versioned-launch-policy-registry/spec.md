## MODIFIED Requirements

### Requirement: Launch policy strategies are version-scoped and runtime-owned
The system SHALL maintain a runtime-owned launch policy registry for supported tools and backends. Each registry strategy SHALL bind one operator prompt policy mode to one or more compatible tool-version ranges and backends.

The registry SHALL be stored as repo-owned YAML under `src/houmao/agents/launch_policy/registry/`.

Each registry document SHALL expose a concrete schema that can represent:

- top-level `schema_version`
- top-level `tool`
- one or more strategy entries with `strategy_id`, `operator_prompt_mode`, `backends`, and `supported_versions`
- strategy `minimal_inputs`
- strategy `evidence`
- strategy `owned_paths`
- strategy `actions`

The `supported_versions` field SHALL use one dependency-style version-specifier expression per strategy entry (for example `>=2.1.81,<2.2`) and strategy resolution SHALL continue to fail explicitly when the detected tool version matches no declared supported range.

#### Scenario: Same tool selects different strategies for different versions
- **WHEN** two installed versions of the same CLI tool request the same operator prompt policy
- **AND WHEN** those versions match different compatible declared supported-version ranges
- **THEN** the registry MAY select different launch policy strategies for those versions
- **AND THEN** strategy selection remains deterministic for a given tool, backend, policy mode, and detected version
