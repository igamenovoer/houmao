# Codex Credential Kinds

Use this reference when `--tool codex` and the agent needs to present credential-kind options to the user during `project credentials codex add` or `credentials codex add --agent-def-dir <path>`.

## Kinds

### 1. API Key

- Looks like: a string value representing an OpenAI API key (typically starts with `sk-`)
- Maps to: `--api-key`
- Choose this when: you have an OpenAI API key or a compatible provider key
- Security: opaque secret; treat as non-recoverable once stored

Optional modifiers when using this kind:

- `--base-url` to override the default OpenAI endpoint
- `--org-id` to pin an OpenAI organization ID

### 2. Cached Login State (auth.json)

- Looks like: a file path to an `auth.json` file from a previous `codex` login
- Maps to: `--auth-json`
- Choose this when: you have an existing Codex `auth.json` file (for example from `~/.codex/auth.json`) containing cached login state
- Security: the file is treated as opaque cached login state

Optional modifiers when using this kind:

- `--base-url` to override the default OpenAI endpoint
- `--org-id` to pin an OpenAI organization ID

## Discovery Note

The `project credentials codex add` and `credentials codex add --agent-def-dir <path>` commands do not run discovery-mode credential creation (auto credentials, env lookup, or directory scan). If you want discovery-mode credential import during creation, use `project easy specialist create` through `houmao-specialist-mgr` instead.
