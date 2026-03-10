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
placeholder `{}` file does not count as usable login state, so launches without
`OPENAI_API_KEY` still require a non-empty top-level JSON object in
`files/auth.json`.

For Claude credential profiles, include `files/claude_state.template.json` as
the launch-time input template for runtime `.claude.json` materialization.
