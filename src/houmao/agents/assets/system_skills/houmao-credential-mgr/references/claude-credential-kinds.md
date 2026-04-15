# Claude Credential Kinds

Use this reference when `--tool claude` and the agent needs to present credential-kind options to the user during `project credentials claude add` or `credentials claude add --agent-def-dir <path>`.

## Kinds

### 1. API Key

- Looks like: a string value starting with `sk-ant-` or similar Anthropic key prefix
- Maps to: `--api-key`
- Choose this when: you have an Anthropic API key from the Anthropic console or a compatible provider
- Security: opaque secret; treat as non-recoverable once stored

Optional modifiers when using this kind:

- `--base-url` to override the default Anthropic endpoint
- `--model` to pin a specific model name

### 2. Auth Token

- Looks like: a string value representing an Anthropic auth token (`ANTHROPIC_AUTH_TOKEN`)
- Maps to: `--auth-token`
- Choose this when: you have an Anthropic-issued auth token distinct from an API key
- Security: opaque secret; treat as non-recoverable once stored

Optional modifiers when using this kind:

- `--base-url` to override the default Anthropic endpoint
- `--model` to pin a specific model name

### 3. OAuth Token

- Looks like: a string value representing a Claude Code OAuth token (`CLAUDE_CODE_OAUTH_TOKEN`)
- Maps to: `--oauth-token`
- Choose this when: you have an OAuth token obtained through Claude Code's OAuth flow
- Security: opaque secret; treat as non-recoverable once stored

Optional modifiers when using this kind:

- `--base-url` to override the default Anthropic endpoint
- `--model` to pin a specific model name

### 4. Vendor-Login Config Directory

- Looks like: a directory path containing `.credentials.json` and optionally companion `.claude.json`
- Maps to: `--config-dir`
- Choose this when: you have an existing Claude vendor-login directory (for example `~/.claude`) that already contains `.credentials.json` from a previous `claude` login
- Security: the `.credentials.json` file is treated as opaque vendor login state; companion `.claude.json` travels with the same config-root lane when present

If the user points at `.credentials.json` directly, resolve its parent directory and use that as `--config-dir`. If the user mentions both `.credentials.json` and `.claude.json`, still use `--config-dir <root>` rather than separate file flags.

## Optional Bootstrap State

- `--state-template-file` accepts a path to a reusable `claude_state.template.json` for runtime bootstrap state
- This is **not** a credential-providing method; it is optional bootstrap state that may accompany any credential kind above

## Discovery Note

The `project credentials claude add` and `credentials claude add --agent-def-dir <path>` commands do not run discovery-mode credential creation (auto credentials, env lookup, or directory scan). If you want discovery-mode credential import during creation, use `project easy specialist create` through `houmao-specialist-mgr` instead.
