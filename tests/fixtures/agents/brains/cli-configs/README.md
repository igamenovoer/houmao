# CLI Config Profiles

Place secret-free, tool-specific config profiles under:

- `agents/brains/cli-configs/codex/<profile>/...`
- `agents/brains/cli-configs/claude/<profile>/...`
- `agents/brains/cli-configs/gemini/<profile>/...`

The brain builder projects the selected profile into the constructed runtime home according to the tool adapter.
