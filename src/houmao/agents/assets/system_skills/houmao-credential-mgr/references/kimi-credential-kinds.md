# Kimi Credential Kinds

Use this reference when `--tool kimi` and the agent needs to present credential-kind options to the user during `project credentials kimi add` or `internals native-agent credentials kimi add --native-agent-root <path>`.

## Kinds

### 1. API Key or Compatible Provider Key

- Looks like: a string value for `KIMI_MODEL_API_KEY`
- Maps to: `--api-key`
- Choose this when: you have a Kimi-compatible model API key and want Houmao to store env-model credential material
- Security: opaque secret; treat as non-recoverable once stored

Optional modifiers when using this kind:

- `--model-name` to store `KIMI_MODEL_NAME`
- `--base-url` to store `KIMI_MODEL_BASE_URL`
- `--provider-type` to store `KIMI_MODEL_PROVIDER_TYPE`
- `--code-base-url` to store `KIMI_CODE_BASE_URL`
- `--code-oauth-host` to store `KIMI_CODE_OAUTH_HOST`
- `--oauth-host` to store `KIMI_OAUTH_HOST`
- `--disable-telemetry` to store `KIMI_DISABLE_TELEMETRY=true`

### 2. Kimi Code Config File

- Looks like: a file path to an existing Kimi `config.toml`
- Maps to: `--config-toml`
- Choose this when: the user already has Kimi Code configuration that should travel with the Houmao credential bundle
- Security: inspect intent before copying because provider config can reference private endpoints or model names

Pair this with `--credential-json` when the user also has Kimi Code OAuth credential state.

### 3. Kimi Code Credential JSON

- Looks like: a file path to `credentials/kimi-code.json`
- Maps to: `--credential-json`
- Choose this when: the user already has Kimi Code credential JSON from an existing Kimi Code home
- Security: the JSON file is treated as opaque login state

Pair this with `--config-toml` when the matching Kimi config should travel with the credential.

### 4. Existing Kimi Code Home

- Looks like: a directory path containing `config.toml` and optionally `credentials/kimi-code.json`
- Maps to: `--code-home`
- Choose this when: the user wants to import both supported Kimi Code files from one existing home
- Security: copy only the supported Kimi files; do not scan unrelated Kimi home contents

## Set and Clear Notes

For `project credentials kimi set` or `internals native-agent credentials kimi set --native-agent-root <path>`, the same input flags update the matching stored env values or files. Clear flags are tool-specific; use only the clear flags exposed by the Kimi `set` command, such as `--clear-model-name`, `--clear-api-key`, `--clear-base-url`, `--clear-provider-type`, `--clear-code-base-url`, `--clear-code-oauth-host`, `--clear-oauth-host`, `--clear-disable-telemetry`, `--clear-config-toml`, and `--clear-credential-json`.

## Login Helper Note

Kimi does not have a maintained Houmao credential login helper in this change. If the user asks to log in to Kimi, explain that they must provide explicit credential inputs through `add` or `set`, such as `--api-key`, `--config-toml`, `--credential-json`, or `--code-home`.

## Discovery Note

The `project credentials kimi add` and `internals native-agent credentials kimi add --native-agent-root <path>` commands do not run discovery-mode credential creation (auto credentials, env lookup, or directory scan). If you want discovery-mode credential import during creation, use `project specialist create` through `houmao-agent-definition` instead.
