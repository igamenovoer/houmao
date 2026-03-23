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
launch_policy:
  operator_prompt_mode: unattended
```

Recipes must reference credential profiles by name only.
Startup no-prompt posture belongs in `launch_policy.operator_prompt_mode`, not in tool-specific checked-in config defaults.

For narrow installed-skill invocation coverage, use `claude/skill-invocation-demo-default.yaml` and `codex/skill-invocation-demo-default.yaml`.

For narrow mailbox/demo coverage, use `claude/mailbox-demo-default.yaml` and `codex/mailbox-demo-default.yaml`.

For the headless mail ping-pong gateway demo, use `claude/mail-ping-pong-initiator-default.yaml` and `codex/mail-ping-pong-responder-default.yaml`.

Keep heavyweight GPU-oriented recipes for repository-scale engineering flows.
