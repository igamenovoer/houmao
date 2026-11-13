# Spec Delta

## REMOVED Requirements

### Requirement: Repo-owned Yunwu Codex setup bundle
**Reason**: The maintained fixture no longer selects a fixed provider endpoint.
**Migration**: Use `api-compatible` with the selected case's explicit Responses endpoint.

### Requirement: Repo-owned Yunwu Codex auth bundle
**Reason**: Reusable live credentials move outside the checkout and no fixed account bundle is required.
**Migration**: Resolve the API case's local key reference into a private run credential.

### Requirement: Yunwu Codex auth bundle supports env-only and login-state auth paths
**Reason**: The vendor-specific fixture contract is replaced by independent API and optional native-login inputs.
**Migration**: Use env-only generic API preparation or explicitly import native Codex login state for tests that select it.

### Requirement: Yunwu-backed Codex brain composition is discoverable
**Reason**: Documented fixture composition becomes provider-neutral.
**Migration**: Use the generic API-compatible preset and shared preparation guidance.

### Requirement: Yunwu-backed Codex profile passes a live smoke prompt
**Reason**: DeepSeek replaces Yunwu as the initial maintained cloud qualification target.
**Migration**: Run the generic Codex cloud smoke against the selected DeepSeek Responses configuration.

## ADDED Requirements

### Requirement: Repo-owned generic API-compatible Codex setup bundle

The repository SHALL provide a secret-free `api-compatible` Codex setup. Prepared config SHALL select its generic provider with the explicitly resolved base URL, `env_key = "OPENAI_API_KEY"`, `requires_openai_auth = false`, and `wire_api = "responses"`. Tracked setup inputs SHALL NOT embed a live key or fixed Yunwu endpoint; unresolved routing SHALL fail preparation.

#### Scenario: Setup bundle selects the generic provider
- **WHEN** a developer prepares Codex with setup `api-compatible` and an explicit compatible endpoint
- **THEN** the runtime config selects that resolved endpoint and the Responses protocol
- **AND THEN** authentication comes from the selected environment credential rather than an inline bearer token
- **AND THEN** tracked setup inputs remain secret-free

### Requirement: Codex API credentials resolve into private local state

The selected API case SHALL map its key and routing into private Codex credential state using `OPENAI_API_KEY` and the configured endpoint. The runtime provider config SHALL agree with that routing. The workflow SHALL NOT require a `yunwu-openai` bundle or repository-local auth fixture. Manifests and reports SHALL contain no resolved key values.

#### Scenario: Auth env file carries launch-time values
- **WHEN** the selected case supplies an API key and endpoint
- **THEN** preparation injects the selected key through the existing allowlisted Codex credential channel
- **AND THEN** the rendered provider base URL matches the selected endpoint
- **AND THEN** committed presets, setups, manifests, and shareable reports contain no secret value

### Requirement: Codex construction preserves env-only and optional login-state inputs

Codex construction SHALL support env-only API credentials without `auth.json` and SHALL retain optional auth-file projection when explicitly selected for a native login test. Generic API case preparation SHALL NOT discover or add native login state as an implicit fallback.

#### Scenario: Builder supports env-only API auth
- **WHEN** the selected private bundle provides the API key and endpoint without `files/auth.json`
- **THEN** brain construction succeeds and receives its environment credentials

#### Scenario: Optional auth json is still projected when present
- **WHEN** a native login test explicitly selects an imported Codex auth file
- **THEN** construction projects that file into its isolated home without requiring committed secret material

### Requirement: API-compatible Codex composition is discoverable

Tracked fixture presets and guidance SHALL identify the generic setup, explicit model/endpoint inputs, and credential source needed to prepare an API-compatible Codex agent. They SHALL NOT require a fixed personal bundle or embedding a key in tracked configuration.

#### Scenario: Developer identifies the builder inputs
- **WHEN** a developer inspects tracked Codex presets or fixture guidance
- **THEN** they can select `api-compatible` and either generic API case with an explicit model and endpoint
- **AND THEN** the guidance explains how the selected key enters private local credential state

### Requirement: API-compatible Codex profile passes a live smoke prompt

The repository SHALL provide a live Codex smoke flow using the generic setup against configured DeepSeek Responses endpoints. The flow SHALL use local credentials, avoid first-party OpenAI login, and record actual client/model/protocol metadata and the observed prompt outcome.

#### Scenario: Codex returns the expected smoke token
- **WHEN** a developer launches the configured cloud Codex case and submits `Respond with exactly this text and nothing else: API_COMPATIBLE_CODEX_SMOKE_OK`
- **THEN** the client reaches the selected DeepSeek Responses endpoint without first-party login
- **AND THEN** the smoke verifies the expected token and retains sanitized qualification evidence

## MODIFIED Requirements

### Requirement: Repo-owned Codex setup bundles avoid fixed model defaults

Repo-owned Codex setup bundles SHALL NOT pin a model solely to provide a default. Setups MAY contain provider routing, supported reasoning defaults, personality, and TUI startup preferences. Model selection SHALL remain explicit launch configuration, and generic fixtures SHALL NOT inherit model-specific reasoning or context assumptions from a prior qualification.

#### Scenario: Default Codex setup carries no model pin
- **WHEN** a developer inspects the repo-owned default setup
- **THEN** it contains no fixed `model` key
- **AND THEN** supported non-model preferences may remain

#### Scenario: Generic setup keeps protocol selection without a model pin
- **WHEN** a developer inspects the tracked `api-compatible` setup
- **THEN** it describes Responses routing and environment-based authentication without a fixed model or account endpoint

#### Scenario: Yunwu Codex setup keeps provider routing without model pin
- **WHEN** a maintained fixture consumer that previously selected the Yunwu setup is migrated
- **THEN** it selects `api-compatible` with an explicit endpoint and model
- **AND THEN** the replacement tracked setup retains Responses routing without preserving a Yunwu endpoint or fixed model

#### Scenario: Explicit provider model remains an operator choice
- **WHEN** a developer prepares a specific compatible model
- **THEN** the selected run receives its explicit model and supported metadata without changing tracked setup defaults
