# Codex Credential Lookup

Use this reference only when `--tool codex` and the active credential-source mode needs tool-specific lookup guidance.

This page is grounded in Codex's official docs, the local `extern/orphan/codex` source checkout, and the installed `codex` executable.

## Maintained Roots And Surfaces

- `CODEX_HOME` is the maintained Codex home override.
- If `CODEX_HOME` is set, treat that directory as the user-level Codex home.
- Otherwise treat `~/.codex` as the normal user-level Codex home.
- User-level config lives in `<CODEX_HOME>/config.toml` or `~/.codex/config.toml`.
- Project-scoped overrides may exist in `<repo-root>/.codex/config.toml`.
- Cached login state may exist in `<CODEX_HOME>/auth.json` or `~/.codex/auth.json` when file-backed credential storage is in use.

## Env Lookup Mode

When the user explicitly points you at env names or patterns, relevant Codex env vars include:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_ORG_ID`
- any provider `env_key` explicitly named by the user or discovered from a selected `config.toml`

Only env values that can be mapped into `--api-key`, `--base-url`, and optional `--codex-org-id` are directly importable.

## Directory Scan Mode

If the user points you at one directory, scan only inside that directory.

If the directory looks like a repo root, inspect only likely Codex paths inside it:

- `.codex/config.toml`
- `.codex/auth.json`

If the directory looks like a Codex home, inspect only likely Codex files inside it:

- `config.toml`
- `auth.json`

Use config files to determine whether a selected provider is importable. Do not assume Codex keyring-only or browser-login state can be recovered from a directory scan.

## Auto Credentials Mode

When the user explicitly asks for `auto credentials`, search in this order:

1. repo-local Codex candidate
2. home-dir Codex candidate
3. current process env

For the repo-local Codex candidate:

- If `CODEX_HOME` is already set and resolves inside the current repo, inspect that directory first.
- Otherwise inspect `<repo-root>/.codex` if it exists.
- Also inspect `<repo-root>/.codex/config.toml` for project-scoped provider selection when it exists.

For the home-dir Codex candidate:

- If `CODEX_HOME` is already set and points under the user's home, inspect that directory first.
- Otherwise inspect `~/.codex`.

Prefer the most specific coherent Codex source:

- repo-local importable provider config plus its env key beats unrelated global login state
- otherwise an importable `auth.json` beats partial config without enough env data

## Importable Forms

Codex auth is directly importable for easy specialist creation only when you can recover one of these supported forms:

- `auth.json`
- `OPENAI_API_KEY` with optional `OPENAI_BASE_URL` and optional `OPENAI_ORG_ID`
- a config-backed env-only provider only when all of these are true:
  - the provider is selected by the active Codex config
  - `requires_openai_auth = false`
  - `wire_api = "responses"`
  - the provider's declared `env_key` is present
  - any needed base URL can be recovered from config or env

Map them to:

- `--codex-auth-json`
- `--api-key`
- `--base-url`
- `--codex-org-id`

## Non-Importable Or Unsupported Codex Shapes

Report failure and ask the user for supported explicit auth when discovery finds only:

- keyring-only or OS-credential-store Codex login state with no readable `auth.json`
- ChatGPT login state that is not materialized into an importable `auth.json`
- a provider config with `requires_openai_auth = true`
- a provider config that depends on unsupported custom headers, unsupported query params, non-Responses wire APIs, or other auth forms that cannot be expressed by the supported create-command flags

Do not assume any Houmao test-fixture paths exist on the deployment host.
