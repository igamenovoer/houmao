---
skill_invocation_notation: >
  Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
  SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
  accepted only as legacy input when SKILL-MAIN.md is absent.
  Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
  `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
  `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
  subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
  by parent subcommand parent. Intermediate subcommands act as object generators.
  Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints.
---

# Kimi Credential Kinds

Use this reference when `--tool kimi` and the agent needs to present credential-kind options to the user during `project credentials kimi add` or `internals native-agent credentials kimi add --native-agent-root <path>`.

## Kinds

### 1. API Key or Compatible Provider Key

- Looks like: a string value for `KIMI_MODEL_API_KEY`
- Maps to: `--api-key`
- Choose this when: you have a Kimi Platform API key or compatible provider key and want Houmao to store env-model credential material
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

- Looks like: a directory path containing `credentials/kimi-code.json` and optionally `config.toml`
- Maps to: `--code-home`
- Choose this when: the user wants to import supported default Kimi Code OAuth state and matching config from one existing home
- Security: copy only the supported Kimi files; do not scan unrelated Kimi home contents

### 5. Fresh Default Kimi Code OAuth Login

- Looks like: a request to run Kimi Code's `kimi login` device-code OAuth flow and import the resulting temporary Kimi Code home
- Maps to: the Kimi Code login-handling workflow, then `--code-home`
- Choose this when: the user wants a new default Kimi Code OAuth credential rather than an API key or existing file
- Security: run the login in an isolated `KIMI_CODE_HOME`, treat `credentials/kimi-code.json` as opaque login state, and do not print raw token JSON

Use `../references/kimi-code-login-handling.md` for this workflow. It runs `kimi login` in tmux, verifies `credentials/kimi-code.json`, and imports with `project credentials kimi add|set --code-home <temp-kimi-home>` or the direct native-agent equivalent. The `project credentials kimi add` command does not itself perform the device-code login.

Non-default Kimi Code OAuth endpoints need extra care. If the user explicitly needs `KIMI_CODE_OAUTH_HOST`, `KIMI_OAUTH_HOST`, or `KIMI_CODE_BASE_URL`, warn that Kimi Code may write a scoped OAuth token file such as `credentials/kimi-code-env-<hash>.json`; current Houmao Kimi `--code-home` import expects `credentials/kimi-code.json` and does not promise support for arbitrary scoped credential filenames.

## Set and Clear Notes

For `project credentials kimi set` or `internals native-agent credentials kimi set --native-agent-root <path>`, the same input flags update the matching stored env values or files. Clear flags are tool-specific; use only the clear flags exposed by the Kimi `set` command, such as `--clear-model-name`, `--clear-api-key`, `--clear-base-url`, `--clear-provider-type`, `--clear-code-base-url`, `--clear-code-oauth-host`, `--clear-oauth-host`, `--clear-disable-telemetry`, `--clear-config-toml`, and `--clear-credential-json`.

## Login Helper Note

Kimi does not have a maintained Houmao credential login helper in this change. Do not run or invent `houmao-mgr project credentials kimi login` or `houmao-mgr internals native-agent credentials kimi login`.

If the user asks for a fresh default Kimi Code OAuth login, use `../references/kimi-code-login-handling.md`; it creates a temporary Kimi Code home with `kimi login` and imports that home with `--code-home`. If the user provides an API key, config file, credential JSON file, or existing Kimi Code home, use explicit credential inputs through `add` or `set`, such as `--api-key`, `--config-toml`, `--credential-json`, or `--code-home`.

## Discovery Note

The `project credentials kimi add` and `internals native-agent credentials kimi add --native-agent-root <path>` commands do not run discovery-mode credential creation (auto credentials, env lookup, or directory scan). If you want discovery-mode credential import during creation, use `project specialist create` through `houmao-shared-routines->houmao-agent-definition` instead.
