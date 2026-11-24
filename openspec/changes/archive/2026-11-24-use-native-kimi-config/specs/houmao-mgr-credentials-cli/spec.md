# Spec Delta

## ADDED Requirements

### Requirement: Kimi credential commands accept native config and private auth inputs

Maintained Kimi credential commands SHALL accept `--config-toml`, `--code-home`, and `--credential-json` for native config and OAuth imports. `--api-key` SHALL supply the private `KIMI_MODEL_API_KEY` binding for a native `api_key_env` reference. Kimi provider and model metadata SHALL be authored in TOML. The command SHALL retire the flags and clear options that author their former env bindings.

#### Scenario: Import a native config for an API-key provider

- **WHEN** an operator adds or updates Kimi credentials with `--config-toml` and `--api-key`
- **THEN** the bundle stores native config and the private key binding
- **AND THEN** it does not store a provider or model selector in `vars.env`
- **AND THEN** credential inspection redacts the key and omits private TOML contents

#### Scenario: Import native OAuth material

- **WHEN** an operator supplies a selected Kimi OAuth home with its supported config and token file
- **THEN** `--code-home` imports the config and token file for the selected credential
- **AND THEN** the import does not require an API key

#### Scenario: Specialist credential authoring uses a native config

- **WHEN** a Kimi specialist workflow is given a custom endpoint and model configuration
- **THEN** the supported credential inputs include a native TOML file and an optional matching private API key
- **AND THEN** using the former Kimi env-model flags fails with guidance to provide the native fields
