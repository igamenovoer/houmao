# Spec Delta

## MODIFIED Requirements

### Requirement: Launch policy strategies are version-scoped and runtime-owned

The system SHALL maintain a runtime-owned launch policy registry for supported tools and backends. Each registry strategy SHALL bind one operator prompt policy mode to compatible tool versions and backends.

The registry SHALL be stored as repo-owned YAML under `src/houmao/agents/launch_policy/registry/`.

Each registry document SHALL expose a concrete schema that can represent:

- top-level `schema_version`
- top-level `tool`
- one or more strategy entries with `strategy_id`, `operator_prompt_mode`, `backends`, and `supported_versions`
- strategy `minimal_inputs`
- strategy `evidence`
- strategy `owned_paths`
- strategy `actions`

Packaged strategies for DSH, Kimi Code, Claude Code, and Codex SHALL declare one inclusive minimum in `supported_versions`, using `>=<version>`. Strategy selection SHALL remain unique for each tool, backend, prompt policy, and eligible detected version.

#### Scenario: A later build selects the applicable minimum-version strategy

- **WHEN** a packaged strategy covers the requested tool, backend, and prompt policy
- **AND WHEN** a detected release or release candidate is at or above its minimum
- **THEN** resolution selects the strategy even if evidence cites an earlier executable version

#### Scenario: Same tool selects different strategies for different versions

- **WHEN** DSH Web runs at its floor and DSH headless runs at its later floor under the same prompt policy
- **THEN** each launch selects the unique strategy for its backend and version

### Requirement: Unattended strategy compatibility failures are explicit

For prompt-forbidden launches, ordinary registry resolution SHALL fail explicitly when the version is missing, unparseable, below the applicable minimum, or outside the accepted release channels. It SHALL report when no compatible strategy covers the requested backend.

#### Scenario: Unknown newer version does not use silent floor fallback

- **WHEN** a newer eligible version has no recorded qualification but meets the minimum declared for its backend
- **THEN** the declared minimum directly selects the applicable strategy

#### Scenario: A detected version is below the minimum or unparseable

- **WHEN** a prompt-forbidden launch detects a below-minimum build or cannot determine its version
- **THEN** unattended strategy resolution fails before provider start with a version compatibility diagnostic
