## MODIFIED Requirements

### Requirement: Repo-owned Yunwu Codex auth bundle
The system SHALL provide a local-only Codex auth bundle named `yunwu-openai` under `tests/fixtures/auth-bundles/codex/yunwu-openai/` that stores the launch-time API key and endpoint routing values in `env/vars.env` using the env var names accepted by the current Codex adapter.

#### Scenario: Auth env file carries launch-time values
- **WHEN** a developer prepares `tests/fixtures/auth-bundles/codex/yunwu-openai/env/vars.env`
- **THEN** the file SHALL support plain-text `OPENAI_API_KEY` and `OPENAI_BASE_URL` entries
- **AND THEN** a Codex launch built from that auth bundle SHALL inject those values into the tool process through the existing auth-env mechanism
- **AND THEN** committed presets, setup bundles, and manifests SHALL NOT contain the secret values themselves
