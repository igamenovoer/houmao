# Codex Credential Kinds

Use this reference when `--tool codex` and the agent needs to present credential-kind options to the user during `project easy specialist create`.

## Kinds

### 1. API Key

- Looks like: a string value representing an OpenAI API key (typically starts with `sk-`)
- Maps to: `--api-key`
- Choose this when: you have an OpenAI API key or a compatible provider key
- Security: opaque secret; treat as non-recoverable once stored

Optional modifiers when using this kind:

- `--base-url` to override the default OpenAI endpoint
- `--codex-org-id` to pin an OpenAI organization ID

### 2. Cached Login State (auth.json)

- Looks like: a file path to an `auth.json` file from a previous `codex` login
- Maps to: `--codex-auth-json`
- Choose this when: you have an existing Codex `auth.json` file (for example from `~/.codex/auth.json`) containing cached login state
- Security: the file is treated as opaque cached login state

Optional modifiers when using this kind:

- `--base-url` to override the default OpenAI endpoint
- `--codex-org-id` to pin an OpenAI organization ID

## Discovery Shortcuts (alternative to picking a kind)

Instead of picking an explicit kind above, the user can ask for one of these discovery modes:

- **Auto credentials** — search the host for existing Codex auth in repo-local homes, user homes, and process env
- **Env lookup** — check specific env vars such as `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_ORG_ID`
- **Directory scan** — scan a specific directory for Codex credential files

Discovery shortcut details live on `references/codex-credential-lookup.md`; load that reference when a discovery shortcut is selected.
