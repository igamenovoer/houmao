# Spec Delta

## ADDED Requirements

### Requirement: Repository SHALL publish a secret-free model-pool template separate from dev-box pool files
The tracked `tests/fixtures/agent-launch/` root SHALL include a secret-free `model-pool.example.toml` template documenting supported pool-entry shapes across self-hosted API, cloud API, and native-login lanes. Actual developer `model-pool.toml` files SHALL remain untracked in the external local fixture store alongside `auth/` and SHALL NOT be committed to `tests/fixtures/`.

#### Scenario: Maintainer inspects tracked model-pool guidance on a fresh checkout
- **WHEN** a maintainer inspects `tests/fixtures/agent-launch/` before configuring local models
- **THEN** `model-pool.example.toml` and `README.md` document how to create an external `model-pool.toml` using placeholder endpoints, binary paths, and credential references without live keys

#### Scenario: Live model-pool file stays in external storage
- **WHEN** a developer configures a working `model-pool.toml` in `${XDG_DATA_HOME:-~/.local/share}/houmao/test-fixtures/`
- **THEN** Git status in the repository remains clean and tracked fixture roots contain no dev-box-specific model URLs or executable paths
