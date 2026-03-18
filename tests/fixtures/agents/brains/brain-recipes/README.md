# Brain Recipe Format

Brain recipes are declarative and secret-free.

```yaml
schema_version: 1
name: <recipe-name>
tool: codex|claude|gemini
skills:
  - <skill-name>
config_profile: <profile-name>
credential_profile: <cred-profile-name>
```

Recipes must reference credential profiles by name only.

For narrow installed-skill invocation coverage, use `claude/skill-invocation-demo-default.yaml` and `codex/skill-invocation-demo-default.yaml`.

For narrow mailbox/demo coverage, use `claude/mailbox-demo-default.yaml` and `codex/mailbox-demo-default.yaml`.

Keep heavyweight GPU-oriented recipes for repository-scale engineering flows.
