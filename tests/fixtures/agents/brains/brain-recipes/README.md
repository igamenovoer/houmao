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
