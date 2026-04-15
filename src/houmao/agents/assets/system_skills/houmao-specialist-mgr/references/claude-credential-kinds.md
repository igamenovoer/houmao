# Claude Credential Kinds

Use this reference when `--tool claude` and the agent needs to present credential-kind options to the user during `project easy specialist create`.

## Kinds

### 1. API Key

- Looks like: a string value starting with `sk-ant-` or similar Anthropic key prefix
- Maps to: `--api-key`
- Choose this when: you have an Anthropic API key from the Anthropic console or a compatible provider
- Security: opaque secret; treat as non-recoverable once stored

Optional modifiers when using this kind:

- `--base-url` to override the default Anthropic endpoint
- `--claude-model` to pin a specific model name

### 2. Auth Token

- Looks like: a string value representing an Anthropic auth token (`ANTHROPIC_AUTH_TOKEN`)
- Maps to: `--claude-auth-token`
- Choose this when: you have an Anthropic-issued auth token distinct from an API key
- Security: opaque secret; treat as non-recoverable once stored

Optional modifiers when using this kind:

- `--base-url` to override the default Anthropic endpoint
- `--claude-model` to pin a specific model name

### 3. OAuth Token

- Looks like: a string value representing a Claude Code OAuth token (`CLAUDE_CODE_OAUTH_TOKEN`)
- Maps to: `--claude-oauth-token`
- Choose this when: you have an OAuth token obtained through Claude Code's OAuth flow
- Security: opaque secret; treat as non-recoverable once stored

Optional modifiers when using this kind:

- `--base-url` to override the default Anthropic endpoint
- `--claude-model` to pin a specific model name

### 4. Vendor-Login Config Directory

- Looks like: a directory path containing `.credentials.json` and optionally companion `.claude.json`
- Maps to: `--claude-config-dir`
- Choose this when: you have an existing Claude vendor-login directory (for example `~/.claude`) that already contains `.credentials.json` from a previous `claude` login
- Security: the `.credentials.json` file is treated as opaque vendor login state; companion `.claude.json` travels with the same config-root lane when present

If the user points at `.credentials.json` directly, resolve its parent directory and use that as `--claude-config-dir`. If the user mentions both `.credentials.json` and `.claude.json`, still use `--claude-config-dir <root>` rather than separate file flags.

## Optional Bootstrap State

- `--claude-state-template-file` accepts a path to a reusable `claude_state.template.json` for runtime bootstrap state
- This is **not** a credential-providing method; it is optional bootstrap state that may accompany any credential kind above

## Discovery Shortcuts (alternative to picking a kind)

Instead of picking an explicit kind above, the user can ask for one of these discovery modes:

- **Auto credentials** — search the host for existing Claude auth in repo-local homes, user homes, and process env
- **Env lookup** — check specific env vars such as `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`
- **Directory scan** — scan a specific directory for Claude credential files

Discovery shortcut details live on `references/claude-credential-lookup.md`; load that reference when a discovery shortcut is selected.
