# Local-Only Credentials

`agents/brains/api-creds/` stores local credential profiles and must stay uncommitted.

Suggested layout:

```text
agents/brains/api-creds/
  <tool>/<cred-profile>/
    files/...
    env/vars.env
```

`vars.env` should contain key/value entries needed by the selected tool adapter.

For the current Codex adapter, custom OpenAI-compatible profiles should store
plain-text `OPENAI_API_KEY` and `OPENAI_BASE_URL` entries in `env/vars.env`.
`files/auth.json` is optional for env-backed Codex profiles; include it only if
you want to project a real local login-state file into the runtime home. A
tracked placeholder or structural stub in the repo must stay secret-free and is
not a substitute for a real local login-state file. Launches without
`OPENAI_API_KEY` still require a non-empty top-level JSON object in the local
ignored `files/auth.json`.

Codex model selection and reasoning effort do not belong in the credential
profile. Keep those defaults in the matching secret-free
`agents/brains/cli-configs/codex/<profile>/config.toml` profile instead. The
tracked Codex fixture profiles currently target `gpt-5.4` with
`model_reasoning_effort = "medium"`.

For Claude credential profiles, include `files/claude_state.template.json` as
the launch-time input template for runtime `.claude.json` materialization.
