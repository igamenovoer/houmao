# Gemini Credential Lookup

Use this reference only when `--tool gemini` and the active credential-source mode needs tool-specific lookup guidance.

This page is grounded in Gemini CLI's official docs, the local `extern/orphan/gemini-cli` source checkout, and the installed `gemini` executable.

## Maintained Roots And Surfaces

- `GEMINI_CLI_HOME` is the maintained Gemini home override.
- If `GEMINI_CLI_HOME` is set, Gemini global storage lives under `${GEMINI_CLI_HOME}/.gemini`.
- Otherwise the normal user-level Gemini root is `~/.gemini`.
- User settings live in `~/.gemini/settings.json` or `${GEMINI_CLI_HOME}/.gemini/settings.json`.
- Project settings may exist in `<repo-root>/.gemini/settings.json`.
- Stored Google login credentials may exist in `.gemini/oauth_creds.json`.
- Gemini CLI also loads environment variables from `.env` files in the current working directory, then parent directories until the project root or home directory, then `~/.env`.

## Env Lookup Mode

When the user explicitly points you at env names or patterns, relevant Gemini env vars include:

- `GEMINI_API_KEY`
- `GOOGLE_GEMINI_BASE_URL`
- `GOOGLE_API_KEY`
- `GOOGLE_GENAI_USE_VERTEXAI`
- `GOOGLE_GENAI_USE_GCA`
- `GOOGLE_APPLICATION_CREDENTIALS`
- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_LOCATION`

The directly importable Gemini forms for easy specialist creation are:

- `GEMINI_API_KEY` with optional `GOOGLE_GEMINI_BASE_URL`
- `GOOGLE_API_KEY` with `GOOGLE_GENAI_USE_VERTEXAI=true`
- OAuth-backed `.gemini/oauth_creds.json`, typically paired with the runtime selecting `GOOGLE_GENAI_USE_GCA=true`

If matched env vars only indicate service-account JSON, generic ADC, or other Google auth that is not directly representable by current create-command flags, report that as unsupported for this command.

## Directory Scan Mode

If the user points you at one directory, scan only inside that directory.

If the directory looks like a repo root, inspect only likely Gemini paths inside it:

- `.gemini/settings.json`
- `.gemini/oauth_creds.json`
- `.env`

If the directory looks like a Gemini home root, inspect only likely Gemini files inside it:

- `.gemini/settings.json`
- `.gemini/oauth_creds.json`
- `.env`

Use settings and `.env` files as evidence of the active Gemini lane. Do not treat generic ADC or service-account configuration as directly importable unless you also find a supported import surface.

## Auto Credentials Mode

When the user explicitly asks for `auto credentials`, search in this order:

1. repo-local Gemini candidate
2. home-dir Gemini candidate
3. current process env

For the repo-local Gemini candidate:

- If `GEMINI_CLI_HOME` is already set and resolves inside the current repo, inspect `${GEMINI_CLI_HOME}/.gemini` first.
- Otherwise inspect `<repo-root>/.gemini` if it exists.
- Also inspect `<repo-root>/.env` because Gemini CLI loads project `.env` files.

For the home-dir Gemini candidate:

- If `GEMINI_CLI_HOME` is already set and points under the user's home, inspect `${GEMINI_CLI_HOME}/.gemini` first.
- Otherwise inspect `~/.gemini`.
- Also inspect `~/.env` because Gemini CLI falls back there when no nearer `.env` supplies auth.

Prefer one coherent Gemini source rather than mixing unrelated OAuth, API-key, and Vertex lanes.

## Importable Forms

Gemini auth is directly importable for easy specialist creation only when you can recover one of these supported forms:

- `.gemini/oauth_creds.json`
- `GEMINI_API_KEY` with optional `GOOGLE_GEMINI_BASE_URL`
- `GOOGLE_API_KEY` with `GOOGLE_GENAI_USE_VERTEXAI=true`

Map them to:

- `--gemini-oauth-creds`
- `--api-key`
- `--base-url`
- `--google-api-key`
- `--use-vertex-ai`

If OAuth credentials are the only importable Gemini source, let Houmao's managed runtime derive `GOOGLE_GENAI_USE_GCA=true` rather than inventing extra auth inputs.

## Non-Importable Or Unsupported Gemini Shapes

Report failure and ask the user for supported explicit auth when discovery finds only:

- `GOOGLE_APPLICATION_CREDENTIALS` service-account JSON without a supported importable Gemini surface
- pure `gcloud` ADC or other Google Cloud default credentials without `.gemini/oauth_creds.json`
- stored API-key state that Gemini can use internally but that is not recoverable as an env value or supported file input for the create command

Do not assume any Houmao test-fixture paths exist on the deployment host.
