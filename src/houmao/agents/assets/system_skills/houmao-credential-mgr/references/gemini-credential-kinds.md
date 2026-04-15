# Gemini Credential Kinds

Use this reference when `--tool gemini` and the agent needs to present credential-kind options to the user during `project credentials gemini add` or `credentials gemini add --agent-def-dir <path>`.

## Kinds

### 1. API Key

- Looks like: a string value representing a Gemini API key
- Maps to: `--api-key`
- Choose this when: you have a Gemini API key from the Google AI Studio console
- Security: opaque secret; treat as non-recoverable once stored

Optional modifier when using this kind:

- `--base-url` to override the default Gemini endpoint

### 2. Vertex AI

- Looks like: a Google API key paired with the Vertex AI selector
- Maps to: `--google-api-key` plus `--use-vertex-ai`
- Choose this when: you want to use Gemini through Google Cloud's Vertex AI service with a Google API key
- Security: opaque secret; treat as non-recoverable once stored

Optional modifier when using this kind:

- `--base-url` to override the default Vertex AI endpoint

### 3. OAuth Credentials File

- Looks like: a file path to an `oauth_creds.json` file (typically at `~/.gemini/oauth_creds.json`)
- Maps to: `--oauth-creds`
- Choose this when: you have an existing Gemini OAuth credentials file from a previous `gemini` login
- Security: the file is treated as opaque Google OAuth login state

## Discovery Note

The `project credentials gemini add` and `credentials gemini add --agent-def-dir <path>` commands do not run discovery-mode credential creation (auto credentials, env lookup, or directory scan). If you want discovery-mode credential import during creation, use `project easy specialist create` through `houmao-specialist-mgr` instead.
