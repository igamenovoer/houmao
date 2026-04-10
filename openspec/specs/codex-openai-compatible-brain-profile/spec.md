# codex-openai-compatible-brain-profile Specification

## Purpose
Define repo-owned Yunwu/OpenAI-compatible Codex setup and auth bundles plus their validation expectations.

## Requirements
### Requirement: Repo-owned Yunwu Codex setup bundle
The system SHALL provide a secret-free Codex setup bundle for a repo-owned OpenAI-compatible provider named `yunwu-openai`.

#### Scenario: Setup bundle selects the Yunwu provider
- **WHEN** a developer builds a Codex runtime selecting setup `yunwu-openai`
- **THEN** the constructed runtime home SHALL contain a `config.toml` that selects `model_provider = "yunwu-openai"`
- **AND THEN** the `yunwu-openai` provider block SHALL set `base_url` to the Yunwu endpoint, `env_key = "OPENAI_API_KEY"`, `requires_openai_auth = false`, and `wire_api = "responses"`
- **AND THEN** the committed setup bundle SHALL remain free of secret values

### Requirement: Repo-owned Yunwu Codex auth bundle
The system SHALL provide a local-only Codex auth bundle named `yunwu-openai` under `tests/fixtures/auth-bundles/codex/yunwu-openai/` that stores the launch-time API key and endpoint routing values in `env/vars.env` using the env var names accepted by the current Codex adapter.

#### Scenario: Auth env file carries launch-time values
- **WHEN** a developer prepares `tests/fixtures/auth-bundles/codex/yunwu-openai/env/vars.env`
- **THEN** the file SHALL support plain-text `OPENAI_API_KEY` and `OPENAI_BASE_URL` entries
- **AND THEN** a Codex launch built from that auth bundle SHALL inject those values into the tool process through the existing auth-env mechanism
- **AND THEN** committed presets, setup bundles, and manifests SHALL NOT contain the secret values themselves

### Requirement: Yunwu Codex auth bundle supports env-only and login-state auth paths
The system SHALL support the `yunwu-openai` Codex auth bundle when authentication is provided either by env-backed provider credentials alone or by those credentials plus a local `auth.json` login-state file.

#### Scenario: Builder supports env-only Yunwu auth
- **WHEN** a developer builds a Codex runtime selecting auth bundle `yunwu-openai`
- **AND WHEN** that local-only auth bundle provides `OPENAI_API_KEY` and `OPENAI_BASE_URL` in `env/vars.env`
- **AND WHEN** the auth bundle does not provide `files/auth.json`
- **THEN** brain construction SHALL still succeed
- **AND THEN** the constructed runtime home SHALL still receive the auth bundle's env-based credentials

#### Scenario: Optional Yunwu auth.json is still projected when present
- **WHEN** a developer builds a Codex runtime selecting auth bundle `yunwu-openai`
- **AND WHEN** that local-only auth bundle also provides `files/auth.json`
- **THEN** the builder SHALL still be able to project that file into the constructed runtime home without requiring committed secret material outside the local-only auth bundle

### Requirement: Yunwu-backed Codex brain composition is discoverable
The system SHALL provide a secret-free preset or equivalent repo-owned guidance that identifies the `yunwu-openai` setup and auth bundle names needed to build the Yunwu-backed Codex agent.

#### Scenario: Developer identifies the Yunwu builder inputs
- **WHEN** a developer inspects the tracked Codex presets or the repo-owned agent fixture docs
- **THEN** they SHALL be able to identify the `yunwu-openai` setup and auth bundle names needed to build the Codex agent
- **AND THEN** the documented workflow SHALL not require embedding API keys in committed files

### Requirement: Yunwu-backed Codex profile passes a live smoke prompt
The system SHALL support a live Codex CLI verification flow for the `yunwu-openai` setup plus auth bundle using valid local credentials.

#### Scenario: Codex returns the exact expected smoke token
- **WHEN** a developer launches a Codex CLI instance using the `yunwu-openai` setup and auth bundle with valid local credentials
- **AND WHEN** they submit the prompt `Respond with exactly this text and nothing else: YUNWU_CODEX_SMOKE_OK`
- **THEN** the CLI SHALL reach the configured Yunwu-backed provider without requiring first-party OpenAI login
- **AND THEN** it SHALL return exactly `YUNWU_CODEX_SMOKE_OK`
