# Local-Only Credentials

Populate the local credential profiles expected by this demo pack under:

```text
agents/brains/api-creds/
  claude/personal-a-default/
    env/vars.env
    files/claude_state.template.json
  codex/yunwu-openai/
    env/vars.env
    files/auth.json   # optional for env-backed Codex
```

The tracked `claude_state.template.json` is non-secret. `vars.env`, `auth.json`, and any login-state files are local-only.
