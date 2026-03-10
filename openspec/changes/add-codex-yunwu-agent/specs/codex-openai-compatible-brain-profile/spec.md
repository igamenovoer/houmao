## ADDED Requirements

### Requirement: Repo-owned Yunwu Codex config profile
The system SHALL provide a secret-free Codex config profile for a repo-owned OpenAI-compatible provider named `yunwu-openai`.

#### Scenario: Config profile selects the Yunwu provider
- **WHEN** a developer builds a Codex brain selecting config profile `yunwu-openai`
- **THEN** the constructed runtime home SHALL contain a `config.toml` that selects `model_provider = "yunwu-openai"`
- **AND THEN** the `yunwu-openai` provider block SHALL set `base_url` to the Yunwu endpoint, `env_key = "OPENAI_API_KEY"`, `requires_openai_auth = false`, and `wire_api = "responses"`
- **AND THEN** the committed config profile SHALL remain free of secret values

### Requirement: Repo-owned Yunwu Codex credential profile
The system SHALL provide a local-only Codex credential profile named `yunwu-openai` that stores the launch-time API key and endpoint routing values in `env/vars.env` using the env var names accepted by the current Codex adapter.

#### Scenario: Credential env file carries launch-time values
- **WHEN** a developer prepares `tests/fixtures/agents/brains/api-creds/codex/yunwu-openai/env/vars.env`
- **THEN** the file SHALL support plain-text `OPENAI_API_KEY` and `OPENAI_BASE_URL` entries
- **AND THEN** a Codex launch built from that profile SHALL inject those values into the tool process through the existing credential-env mechanism
- **AND THEN** committed recipes, config profiles, and manifests SHALL NOT contain the secret values themselves

### Requirement: Yunwu Codex credential profile supports env-only and login-state auth paths
The system SHALL support the `yunwu-openai` Codex credential profile when authentication is provided either by env-backed provider credentials alone or by those credentials plus a local `auth.json` login-state file.

#### Scenario: Builder supports env-only Yunwu credentials
- **WHEN** a developer builds a Codex brain selecting credential profile `yunwu-openai`
- **AND WHEN** that local-only credential profile provides `OPENAI_API_KEY` and `OPENAI_BASE_URL` in `env/vars.env`
- **AND WHEN** the profile does not provide `files/auth.json`
- **THEN** brain construction SHALL still succeed
- **AND THEN** the constructed runtime home SHALL still receive the profile’s env-based credentials

#### Scenario: Optional Yunwu auth.json is still projected when present
- **WHEN** a developer builds a Codex brain selecting credential profile `yunwu-openai`
- **AND WHEN** that local-only credential profile also provides `files/auth.json`
- **THEN** the builder SHALL still be able to project that file into the constructed runtime home without requiring committed secret material outside the local-only credential profile

### Requirement: Yunwu-backed Codex brain composition is discoverable
The system SHALL provide a secret-free recipe or equivalent repo-owned guidance that identifies the `yunwu-openai` config and credential profile names needed to build the Yunwu-backed Codex agent.

#### Scenario: Developer identifies the Yunwu builder inputs
- **WHEN** a developer inspects the Codex brain recipes or the repo-owned brain fixture docs
- **THEN** they SHALL be able to identify the `yunwu-openai` profile names needed to build the Codex agent
- **AND THEN** the documented workflow SHALL not require embedding API keys in committed files

### Requirement: Yunwu-backed Codex profile passes a live smoke prompt
The system SHALL support a live Codex CLI verification flow for the `yunwu-openai` profile using valid local credentials.

#### Scenario: Codex returns the exact expected smoke token
- **WHEN** a developer launches a Codex CLI instance using the `yunwu-openai` config and credential profiles with valid local credentials
- **AND WHEN** they submit the prompt `Respond with exactly this text and nothing else: YUNWU_CODEX_SMOKE_OK`
- **THEN** the CLI SHALL reach the configured Yunwu-backed provider without requiring first-party OpenAI login
- **AND THEN** it SHALL return exactly `YUNWU_CODEX_SMOKE_OK`
