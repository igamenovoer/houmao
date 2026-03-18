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

For narrow mailbox/demo coverage, use the tracked `claude/mailbox-demo-default.yaml` and `codex/mailbox-demo-default.yaml` recipes instead of the heavyweight GPU-oriented defaults.
