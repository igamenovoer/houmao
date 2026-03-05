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

For Claude credential profiles, include `files/claude_state.template.json` as
the launch-time input template for runtime `.claude.json` materialization.
